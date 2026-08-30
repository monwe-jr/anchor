import json
import sqlite3
from datetime import datetime, timezone

from db.schema import get_connection
from engine.types import Engine, Message
from generation.chunker import chunk_text
from ingest.types import IngestResult

NOTES_AND_FLASHCARDS_SCHEMA = {
    "type": "object",
    "properties": {
        "notes": {"type": "array", "items": {"type": "string"}},
        "flashcards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "answer": {"type": "string"},
                },
                "required": ["question", "answer"],
            },
        },
    },
    "required": ["notes", "flashcards"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _create_document(conn: sqlite3.Connection, ingest_result: IngestResult) -> int:
    cursor = conn.execute(
        "INSERT INTO documents (source_name, source_type, full_text, created_at) "
        "VALUES (?, ?, ?, ?)",
        (ingest_result.source_name, ingest_result.source_type, ingest_result.text, _now()),
    )
    conn.commit()
    return cursor.lastrowid


def _create_job(conn: sqlite3.Connection, document_id: int) -> int:
    now = _now()
    cursor = conn.execute(
        "INSERT INTO jobs (document_id, status, current_stage, error_message, created_at, updated_at) "
        "VALUES (?, 'pending', NULL, NULL, ?, ?)",
        (document_id, now, now),
    )
    conn.commit()
    return cursor.lastrowid


def _update_job(
    conn: sqlite3.Connection,
    job_id: int,
    status: str,
    current_stage: str | None = None,
    error_message: str | None = None,
) -> None:
    conn.execute(
        "UPDATE jobs SET status = ?, current_stage = ?, error_message = ?, updated_at = ? WHERE id = ?",
        (status, current_stage, error_message, _now(), job_id),
    )
    conn.commit()


def create_job(conn: sqlite3.Connection, ingest_result: IngestResult) -> tuple[int, int]:
    """Create the document and its pending job row, committing immediately.

    Split out from `run_pipeline_stages` so callers (e.g. the /ingest endpoint)
    can hand the caller a document_id/job_id right away and run the actual
    processing stages in the background, rather than blocking the request
    until generation finishes.
    """
    document_id = _create_document(conn, ingest_result)
    job_id = _create_job(conn, document_id)
    return document_id, job_id


async def run_pipeline_stages(
    conn: sqlite3.Connection,
    document_id: int,
    job_id: int,
    ingest_result: IngestResult,
    engine: Engine,
) -> int:
    try:
        # --- chunking ---
        _update_job(conn, job_id, status="chunking", current_stage="chunking")
        chunks = chunk_text(ingest_result.text)
        for index, chunk in enumerate(chunks):
            conn.execute(
                "INSERT INTO chunks (document_id, chunk_index, text, embedding) VALUES (?, ?, ?, NULL)",
                (document_id, index, chunk),
            )
        conn.commit()

        # --- embedding ---
        _update_job(conn, job_id, status="embedding", current_stage="embedding")
        embeddings = await engine.embed(chunks) if chunks else []
        chunk_rows = conn.execute(
            "SELECT id, chunk_index FROM chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_id,),
        ).fetchall()
        for row, embedding in zip(chunk_rows, embeddings):
            conn.execute(
                "UPDATE chunks SET embedding = ? WHERE id = ?",
                (json.dumps(embedding), row["id"]),
            )
        conn.commit()

        # --- generating ---
        _update_job(conn, job_id, status="generating", current_stage="generating")
        messages = [
            Message(
                role="system",
                content=(
                    "You produce structured study material from source text. "
                    "Return concise notes and question/answer flashcards."
                ),
            ),
            Message(role="user", content=ingest_result.text),
        ]
        result = await engine.structured(messages, NOTES_AND_FLASHCARDS_SCHEMA)

        for note in result["notes"]:
            conn.execute(
                "INSERT INTO notes (document_id, content) VALUES (?, ?)",
                (document_id, note),
            )
        for card in result["flashcards"]:
            conn.execute(
                "INSERT INTO flashcards (document_id, question, answer) VALUES (?, ?, ?)",
                (document_id, card["question"], card["answer"]),
            )
        conn.commit()

        # --- done ---
        _update_job(conn, job_id, status="done", current_stage=None)
        return job_id

    except Exception as exc:
        conn.rollback()
        # current_stage was already committed by the last _update_job call for
        # the stage that was running when this failed; preserve it so callers
        # can tell which stage the job died in, instead of clearing it to None.
        failed_stage_row = conn.execute(
            "SELECT current_stage FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        failed_stage = failed_stage_row["current_stage"] if failed_stage_row else None
        _update_job(conn, job_id, status="failed", current_stage=failed_stage, error_message=str(exc))
        raise


async def run_pipeline(
    ingest_result: IngestResult,
    engine: Engine,
    conn: sqlite3.Connection | None = None,
) -> int:
    owns_connection = conn is None
    if conn is None:
        conn = get_connection()

    try:
        document_id, job_id = create_job(conn, ingest_result)
        return await run_pipeline_stages(conn, document_id, job_id, ingest_result, engine)
    finally:
        if owns_connection:
            conn.close()
