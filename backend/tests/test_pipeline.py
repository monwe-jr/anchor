import json
import sqlite3
from typing import Any

import pytest

from db.schema import init_db
from engine.types import CompletionResult, Message
from generation.chunker import chunk_text
from generation.pipeline import run_pipeline
from ingest.types import IngestResult


class FakeEngine:
    """Canned Engine: returns fixed embeddings and a fixed structured response."""

    def __init__(self, notes=None, flashcards=None, fail_on_generate: bool = False) -> None:
        self.embed_calls: list[list[str]] = []
        self.structured_calls: list[tuple[list[Message], dict[str, Any]]] = []
        self._notes = notes if notes is not None else ["note one", "note two"]
        self._flashcards = (
            flashcards if flashcards is not None else [{"question": "Q1", "answer": "A1"}]
        )
        self._fail_on_generate = fail_on_generate

    async def complete(self, messages: list[Message]) -> CompletionResult:
        raise NotImplementedError

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(texts)
        return [[float(i), float(i) + 0.5] for i in range(len(texts))]

    async def structured(self, messages: list[Message], schema: dict[str, Any]) -> dict[str, Any]:
        self.structured_calls.append((messages, schema))
        if self._fail_on_generate:
            raise RuntimeError("engine failed during generation")
        return {"notes": self._notes, "flashcards": self._flashcards}


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    init_db(connection)
    yield connection
    connection.close()


def _sample_ingest_result() -> IngestResult:
    return IngestResult(
        text="Photosynthesis converts light energy into chemical energy in plants.",
        source_type="text",
        source_name="bio-notes",
        metadata={"char_count": 70},
    )


async def test_successful_run_persists_everything_and_marks_job_done(conn):
    ingest_result = _sample_ingest_result()
    engine = FakeEngine()

    job_id = await run_pipeline(ingest_result, engine, conn=conn)

    document = conn.execute("SELECT * FROM documents").fetchone()
    assert document["source_name"] == "bio-notes"
    assert document["source_type"] == "text"
    assert document["full_text"] == ingest_result.text

    expected_chunks = chunk_text(ingest_result.text)
    chunk_rows = conn.execute(
        "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index", (document["id"],)
    ).fetchall()
    assert len(chunk_rows) == len(expected_chunks)
    for row in chunk_rows:
        assert row["embedding"] is not None
        assert isinstance(json.loads(row["embedding"]), list)

    note_rows = conn.execute("SELECT content FROM notes WHERE document_id = ?", (document["id"],)).fetchall()
    assert [r["content"] for r in note_rows] == ["note one", "note two"]

    flashcard_rows = conn.execute(
        "SELECT question, answer FROM flashcards WHERE document_id = ?", (document["id"],)
    ).fetchall()
    assert [(r["question"], r["answer"]) for r in flashcard_rows] == [("Q1", "A1")]

    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    assert job["status"] == "done"
    assert job["current_stage"] is None
    assert job["error_message"] is None
    assert engine.embed_calls == [expected_chunks]


async def test_failure_during_generation_marks_job_failed_and_keeps_earlier_stage_data(conn):
    ingest_result = _sample_ingest_result()
    engine = FakeEngine(fail_on_generate=True)

    with pytest.raises(RuntimeError, match="engine failed during generation"):
        await run_pipeline(ingest_result, engine, conn=conn)

    document = conn.execute("SELECT * FROM documents").fetchone()
    assert document is not None

    chunk_rows = conn.execute(
        "SELECT * FROM chunks WHERE document_id = ?", (document["id"],)
    ).fetchall()
    assert len(chunk_rows) == len(chunk_text(ingest_result.text))
    for row in chunk_rows:
        assert row["embedding"] is not None

    assert conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM flashcards").fetchone()[0] == 0

    job = conn.execute("SELECT * FROM jobs WHERE document_id = ?", (document["id"],)).fetchone()
    assert job["status"] == "failed"
    assert job["error_message"] == "engine failed during generation"
