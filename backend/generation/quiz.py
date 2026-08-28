import json
import sqlite3
from dataclasses import dataclass
from typing import Literal

from db.schema import get_connection
from engine.types import Engine, Message

Difficulty = Literal["beginner", "intermediate", "advanced"]

QUIZ_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "correct_option_index": {"type": "integer"},
                    "topic": {"type": "string"},
                },
                "required": ["question", "options", "correct_option_index", "topic"],
            },
        },
    },
    "required": ["questions"],
}


@dataclass(frozen=True)
class QuizQuestion:
    id: int
    document_id: int
    question: str
    options: list[str]
    correct_option_index: int
    topic: str
    difficulty: str


def _document_content(conn: sqlite3.Connection, document_id: int) -> str:
    rows = conn.execute(
        "SELECT text FROM chunks WHERE document_id = ? ORDER BY chunk_index", (document_id,)
    ).fetchall()
    return "\n\n".join(row["text"] for row in rows)


async def generate_quiz(
    document_id: int,
    engine: Engine,
    count: int = 10,
    difficulty: Difficulty = "intermediate",
    conn: sqlite3.Connection | None = None,
) -> list[QuizQuestion]:
    """Generate `count` multiple-choice questions grounded in a document's chunks
    and persist them to quiz_questions."""
    owns_connection = conn is None
    if conn is None:
        conn = get_connection()

    try:
        content = _document_content(conn, document_id)
        messages = [
            Message(
                role="system",
                content=(
                    "You write multiple-choice quiz questions grounded strictly in the "
                    f"provided source text. Write exactly {count} questions at {difficulty} "
                    "difficulty. Each question has exactly 4 options, exactly one of which is "
                    "correct, and a short topic label grouping it with related questions."
                ),
            ),
            Message(role="user", content=content),
        ]
        result = await engine.structured(messages, QUIZ_SCHEMA)

        questions: list[QuizQuestion] = []
        for q in result["questions"]:
            cursor = conn.execute(
                "INSERT INTO quiz_questions "
                "(document_id, question, options, correct_option_index, topic, difficulty) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    document_id,
                    q["question"],
                    json.dumps(q["options"]),
                    q["correct_option_index"],
                    q["topic"],
                    difficulty,
                ),
            )
            questions.append(
                QuizQuestion(
                    id=cursor.lastrowid,
                    document_id=document_id,
                    question=q["question"],
                    options=q["options"],
                    correct_option_index=q["correct_option_index"],
                    topic=q["topic"],
                    difficulty=difficulty,
                )
            )
        conn.commit()
        return questions
    finally:
        if owns_connection:
            conn.close()
