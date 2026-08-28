import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

import pytest

from db.schema import init_db
from engine.types import CompletionResult, Message
from generation.quiz import generate_quiz


class FakeEngine:
    """Canned Engine: returns a fixed structured quiz response."""

    def __init__(self, questions=None) -> None:
        self.structured_calls: list[tuple[list[Message], dict[str, Any]]] = []
        self._questions = (
            questions
            if questions is not None
            else [
                {
                    "question": "What is photosynthesis?",
                    "options": ["A metabolic process", "A rock", "A planet", "A color"],
                    "correct_option_index": 0,
                    "topic": "Photosynthesis",
                },
                {
                    "question": "Where does the Calvin cycle occur?",
                    "options": ["Nucleus", "Mitochondria", "Stroma", "Cytoplasm"],
                    "correct_option_index": 2,
                    "topic": "Calvin Cycle",
                },
            ]
        )

    async def complete(self, messages: list[Message]) -> CompletionResult:
        raise NotImplementedError

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    async def structured(self, messages: list[Message], schema: dict[str, Any]) -> dict[str, Any]:
        self.structured_calls.append((messages, schema))
        return {"questions": self._questions}


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    init_db(connection)
    yield connection
    connection.close()


def _seed_document_with_chunks(conn: sqlite3.Connection) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO documents (source_name, source_type, full_text, created_at) VALUES (?, ?, ?, ?)",
        ("bio-notes", "text", "Photosynthesis converts light energy into chemical energy.", now),
    )
    document_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO chunks (document_id, chunk_index, text, embedding) VALUES (?, ?, ?, NULL)",
        (document_id, 0, "Photosynthesis converts light energy into chemical energy."),
    )
    conn.commit()
    return document_id


async def test_generate_quiz_persists_questions_from_structured_response(conn):
    document_id = _seed_document_with_chunks(conn)
    engine = FakeEngine()

    questions = await generate_quiz(document_id, engine, count=2, difficulty="beginner", conn=conn)

    assert len(questions) == 2
    assert len(engine.structured_calls) == 1

    rows = conn.execute(
        "SELECT * FROM quiz_questions WHERE document_id = ? ORDER BY id", (document_id,)
    ).fetchall()
    assert len(rows) == 2

    assert rows[0]["question"] == "What is photosynthesis?"
    assert json.loads(rows[0]["options"]) == ["A metabolic process", "A rock", "A planet", "A color"]
    assert rows[0]["correct_option_index"] == 0
    assert rows[0]["topic"] == "Photosynthesis"
    assert rows[0]["difficulty"] == "beginner"

    assert rows[1]["question"] == "Where does the Calvin cycle occur?"
    assert rows[1]["correct_option_index"] == 2
    assert rows[1]["topic"] == "Calvin Cycle"

    assert questions[0].id == rows[0]["id"]
    assert questions[0].document_id == document_id
    assert questions[0].options == ["A metabolic process", "A rock", "A planet", "A color"]


async def test_generate_quiz_grounds_the_prompt_in_document_chunk_text(conn):
    document_id = _seed_document_with_chunks(conn)
    engine = FakeEngine()

    await generate_quiz(document_id, engine, conn=conn)

    messages, schema = engine.structured_calls[0]
    user_message = next(m for m in messages if m.role == "user")
    assert "Photosynthesis converts light energy into chemical energy." in user_message.content
    assert schema["required"] == ["questions"]
