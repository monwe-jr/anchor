"""Per-topic mastery: percent correct across all quiz_attempts for a document,
grouped by the topic label on each quiz_questions row."""

import sqlite3
from dataclasses import dataclass

from db.schema import get_connection


@dataclass(frozen=True)
class TopicMastery:
    topic: str
    total_attempts: int
    correct_attempts: int
    mastery_percent: float


def compute_mastery(document_id: int, conn: sqlite3.Connection | None = None) -> list[TopicMastery]:
    owns_connection = conn is None
    if conn is None:
        conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT q.topic AS topic,
                   COUNT(a.id) AS total_attempts,
                   SUM(CASE WHEN a.correct THEN 1 ELSE 0 END) AS correct_attempts
            FROM quiz_attempts a
            JOIN quiz_questions q ON q.id = a.question_id
            WHERE q.document_id = ?
            GROUP BY q.topic
            ORDER BY q.topic
            """,
            (document_id,),
        ).fetchall()

        return [
            TopicMastery(
                topic=row["topic"],
                total_attempts=row["total_attempts"],
                correct_attempts=row["correct_attempts"] or 0,
                mastery_percent=round(100.0 * (row["correct_attempts"] or 0) / row["total_attempts"], 1),
            )
            for row in rows
        ]
    finally:
        if owns_connection:
            conn.close()
