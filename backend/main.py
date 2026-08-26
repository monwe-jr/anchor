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