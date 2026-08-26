import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from db.schema import get_connection, init_db
from engine.ollama import OllamaEngine
from engine.resilient import resilient
from generation.pipeline import run_pipeline
from ingest import ingest
from rag.chat import answer_question
from study.fsrs import Grade
from study.scheduler import get_due_cards, record_review


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = get_connection()
    try:
        init_db(conn)
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
        job_id = await run_pipeline(ingest_result, _engine, conn=conn)
        row = conn.execute("SELECT document_id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    finally:
        conn.close()

    return IngestResponse(document_id=row["document_id"], job_id=job_id)


class DocumentSummary(BaseModel):
    id: int
    source_name: str
    source_type: str
    created_at: str
    job_status: str | None = None


@app.get("/documents")
def list_documents() -> list[DocumentSummary]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT d.id, d.source_name, d.source_type, d.created_at, j.status AS job_status
            FROM documents d
            LEFT JOIN jobs j ON j.id = (
                SELECT id FROM jobs WHERE document_id = d.id ORDER BY id DESC LIMIT 1
            )
            ORDER BY d.id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    return [
        DocumentSummary(
            id=row["id"],
            source_name=row["source_name"],
            source_type=row["source_type"],
            created_at=row["created_at"],
            job_status=row["job_status"],
        )
        for row in rows
    ]


def _require_document(conn, document_id: int) -> None:
    row = conn.execute("SELECT id FROM documents WHERE id = ?", (document_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")


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