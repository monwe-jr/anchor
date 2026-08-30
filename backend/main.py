import asyncio
import json
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from db.schema import get_connection, init_db
from documents.service import delete_document as delete_document_cascade
from documents.service import rename_document
from engine.ollama import OllamaEngine
from engine.resilient import resilient
from generation.pipeline import create_job, recover_interrupted_jobs, run_pipeline_stages
from generation.quiz import Difficulty, generate_quiz
from ingest import ingest
from rag.chat import answer_question
from study.fsrs import Grade
from study.mastery import compute_mastery
from study.scheduler import get_due_cards, record_review


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    try:
        init_db(conn)
        # Any job still "pending"/"chunking"/"embedding"/"generating" here
        # belongs to a process that no longer exists (the previous run died
        # or was restarted mid-job) — reconcile it before serving requests.
        recover_interrupted_jobs(conn)
    finally:
        conn.close()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_engine = resilient(OllamaEngine())


@app.get("/health")
def health():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    question: str
    document_id: int | None = None


class ChatCitation(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    quote: str
    chunk_text: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation]


@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    result = await answer_question(request.question, _engine, document_id=request.document_id)
    return ChatResponse(
        answer=result.answer,
        citations=[
            ChatCitation(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                chunk_index=c.chunk_index,
                quote=c.quote,
                chunk_text=c.chunk_text,
            )
            for c in result.citations
        ],
    )


class IngestTextRequest(BaseModel):
    text: str


class IngestResponse(BaseModel):
    document_id: int
    job_id: int


_UPLOAD_EXTENSION_TO_SOURCE_TYPE = {".pdf": "pdf", ".docx": "docx"}

# asyncio only holds a weak reference to a task, so a background pipeline run
# must be kept alive here or it can be garbage-collected mid-flight.
_background_pipeline_tasks: set[asyncio.Task] = set()


def _run_pipeline_in_background(document_id: int, job_id: int, ingest_result) -> None:
    async def _runner() -> None:
        conn = get_connection()
        try:
            await run_pipeline_stages(conn, document_id, job_id, ingest_result, _engine)
        except Exception:
            # Failure is already recorded on the job row by run_pipeline_stages;
            # there's no request left to propagate the exception to.
            pass
        finally:
            conn.close()

    task = asyncio.create_task(_runner())
    _background_pipeline_tasks.add(task)
    task.add_done_callback(_background_pipeline_tasks.discard)


@app.post("/ingest")
async def ingest_document(request: Request) -> IngestResponse:
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        upload = form.get("file")
        if upload is None or isinstance(upload, str):
            raise HTTPException(status_code=400, detail="Multipart upload must include a 'file' field")

        suffix = Path(upload.filename or "").suffix.lower()
        source_type = _UPLOAD_EXTENSION_TO_SOURCE_TYPE.get(suffix)
        if source_type is None:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload.filename!r}")

        contents = await upload.read()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        try:
            ingest_result = ingest(tmp_path, source_type)
        finally:
            os.unlink(tmp_path)
    else:
        try:
            payload = IngestTextRequest.model_validate(await request.json())
        except (ValueError, ValidationError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        ingest_result = ingest(payload.text, "text")

    conn = get_connection()
    try:
        document_id, job_id = create_job(conn, ingest_result)
    finally:
        conn.close()

    _run_pipeline_in_background(document_id, job_id, ingest_result)

    return IngestResponse(document_id=document_id, job_id=job_id)


class DocumentSummary(BaseModel):
    id: int
    source_name: str
    display_name: str
    source_type: str
    created_at: str
    job_status: str | None = None
    current_stage: str | None = None
    error_message: str | None = None


_DOCUMENT_SELECT_SQL = """
    SELECT d.id, d.source_name, d.display_name, d.source_type, d.created_at,
           j.status AS job_status, j.current_stage, j.error_message
    FROM documents d
    LEFT JOIN jobs j ON j.id = (
        SELECT id FROM jobs WHERE document_id = d.id ORDER BY id DESC LIMIT 1
    )
"""


def _document_summary_from_row(row) -> DocumentSummary:
    return DocumentSummary(
        id=row["id"],
        source_name=row["source_name"],
        display_name=row["display_name"] or row["source_name"],
        source_type=row["source_type"],
        created_at=row["created_at"],
        job_status=row["job_status"],
        current_stage=row["current_stage"],
        error_message=row["error_message"],
    )


@app.get("/documents")
def list_documents() -> list[DocumentSummary]:
    conn = get_connection()
    try:
        rows = conn.execute(f"{_DOCUMENT_SELECT_SQL} ORDER BY d.id DESC").fetchall()
    finally:
        conn.close()

    return [_document_summary_from_row(row) for row in rows]


def _require_document(conn, document_id: int) -> None:
    row = conn.execute("SELECT id FROM documents WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")


@app.get("/documents/{document_id}")
def get_document(document_id: int) -> DocumentSummary:
    conn = get_connection()
    try:
        row = conn.execute(f"{_DOCUMENT_SELECT_SQL} WHERE d.id = ?", (document_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    finally:
        conn.close()

    return _document_summary_from_row(row)


class DocumentUpdateRequest(BaseModel):
    display_name: str


@app.patch("/documents/{document_id}")
def update_document(document_id: int, request: DocumentUpdateRequest) -> DocumentSummary:
    display_name = request.display_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="display_name must not be empty")

    conn = get_connection()
    try:
        _require_document(conn, document_id)
        rename_document(conn, document_id, display_name)
        conn.commit()
        row = conn.execute(f"{_DOCUMENT_SELECT_SQL} WHERE d.id = ?", (document_id,)).fetchone()
    finally:
        conn.close()

    return _document_summary_from_row(row)


@app.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int) -> None:
    conn = get_connection()
    try:
        _require_document(conn, document_id)
        try:
            delete_document_cascade(conn, document_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    finally:
        conn.close()


class Note(BaseModel):
    id: int
    content: str


@app.get("/documents/{document_id}/notes")
def get_document_notes(document_id: int) -> list[Note]:
    conn = get_connection()
    try:
        _require_document(conn, document_id)
        rows = conn.execute(
            "SELECT id, content FROM notes WHERE document_id = ? ORDER BY id", (document_id,)
        ).fetchall()
    finally:
        conn.close()

    return [Note(id=row["id"], content=row["content"]) for row in rows]


class Flashcard(BaseModel):
    id: int
    question: str
    answer: str


@app.get("/documents/{document_id}/flashcards")
def get_document_flashcards(document_id: int) -> list[Flashcard]:
    conn = get_connection()
    try:
        _require_document(conn, document_id)
        rows = conn.execute(
            "SELECT id, question, answer FROM flashcards WHERE document_id = ? ORDER BY id",
            (document_id,),
        ).fetchall()
    finally:
        conn.close()

    return [Flashcard(id=row["id"], question=row["question"], answer=row["answer"]) for row in rows]


class DueCard(BaseModel):
    id: int
    document_id: int
    question: str
    answer: str


@app.get("/review/due")
def review_due(limit: int = 20) -> list[DueCard]:
    conn = get_connection()
    try:
        rows = get_due_cards(limit, conn=conn)
    finally:
        conn.close()

    return [
        DueCard(id=row["id"], document_id=row["document_id"], question=row["question"], answer=row["answer"])
        for row in rows
    ]


class ReviewRequest(BaseModel):
    grade: Grade


@app.post("/review/{flashcard_id}")
def review_flashcard(flashcard_id: int, request: ReviewRequest) -> dict:
    conn = get_connection()
    try:
        row = conn.execute("SELECT id FROM flashcards WHERE id = ?", (flashcard_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Flashcard {flashcard_id} not found")
        record_review(flashcard_id, request.grade, conn=conn)
    finally:
        conn.close()

    return {"status": "ok"}


class QuizGenerateRequest(BaseModel):
    count: int = 10
    difficulty: Difficulty = "intermediate"


class QuizQuestionOut(BaseModel):
    id: int
    question: str
    options: list[str]
    topic: str
    difficulty: str


def _quiz_question_out(row) -> QuizQuestionOut:
    return QuizQuestionOut(
        id=row["id"],
        question=row["question"],
        options=json.loads(row["options"]),
        topic=row["topic"],
        difficulty=row["difficulty"],
    )


@app.post("/documents/{document_id}/quiz")
async def create_document_quiz(document_id: int, request: QuizGenerateRequest) -> list[QuizQuestionOut]:
    conn = get_connection()
    try:
        _require_document(conn, document_id)
        questions = await generate_quiz(
            document_id, _engine, count=request.count, difficulty=request.difficulty, conn=conn
        )
    finally:
        conn.close()

    return [
        QuizQuestionOut(
            id=q.id, question=q.question, options=q.options, topic=q.topic, difficulty=q.difficulty
        )
        for q in questions
    ]


@app.get("/documents/{document_id}/quiz")
def get_document_quiz(document_id: int) -> list[QuizQuestionOut]:
    conn = get_connection()
    try:
        _require_document(conn, document_id)
        rows = conn.execute(
            "SELECT id, question, options, topic, difficulty FROM quiz_questions "
            "WHERE document_id = ? ORDER BY id",
            (document_id,),
        ).fetchall()
    finally:
        conn.close()

    return [_quiz_question_out(row) for row in rows]


class QuizAttemptRequest(BaseModel):
    chosen_option_index: int


class QuizAttemptResponse(BaseModel):
    correct: bool
    correct_option_index: int


@app.post("/quiz/{question_id}/attempt")
def submit_quiz_attempt(question_id: int, request: QuizAttemptRequest) -> QuizAttemptResponse:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT correct_option_index FROM quiz_questions WHERE id = ?", (question_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Quiz question {question_id} not found")

        correct_option_index = row["correct_option_index"]
        correct = request.chosen_option_index == correct_option_index
        conn.execute(
            "INSERT INTO quiz_attempts (question_id, chosen_option_index, correct, answered_at) "
            "VALUES (?, ?, ?, ?)",
            (question_id, request.chosen_option_index, correct, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()

    return QuizAttemptResponse(correct=correct, correct_option_index=correct_option_index)


class TopicMasteryOut(BaseModel):
    topic: str
    total_attempts: int
    correct_attempts: int
    mastery_percent: float


@app.get("/documents/{document_id}/mastery")
def get_document_mastery(document_id: int) -> list[TopicMasteryOut]:
    conn = get_connection()
    try:
        _require_document(conn, document_id)
        mastery = compute_mastery(document_id, conn=conn)
    finally:
        conn.close()

    return [
        TopicMasteryOut(
            topic=m.topic,
            total_attempts=m.total_attempts,
            correct_attempts=m.correct_attempts,
            mastery_percent=m.mastery_percent,
        )
        for m in mastery
    ]