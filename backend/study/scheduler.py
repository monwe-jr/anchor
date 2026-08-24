"""DB-touching half of spaced repetition scheduling.

Reads/writes review_state and delegates all algorithmic decisions to the
pure functions in study/fsrs.py.
"""

import sqlite3
from datetime import datetime, timezone

from db.schema import get_connection
from study.fsrs import Grade, ReviewState
from study.fsrs import review as fsrs_review


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def get_due_cards(limit: int, conn: sqlite3.Connection | None = None) -> list[sqlite3.Row]:
    """Flashcards due for review: never-reviewed cards, or ones past their due_date."""
    owns_connection = conn is None
    if conn is None:
        conn = get_connection()
    try:
        now = _now().isoformat()
        return conn.execute(
            """
            SELECT f.id, f.document_id, f.question, f.answer,
                   rs.due_date, rs.stability, rs.difficulty, rs.review_count
            FROM flashcards f
            LEFT JOIN review_state rs ON rs.flashcard_id = f.id
            WHERE rs.flashcard_id IS NULL OR rs.due_date <= ?
            ORDER BY COALESCE(rs.due_date, ?) ASC
            LIMIT ?
            """,
            (now, now, limit),
        ).fetchall()
    finally:
        if owns_connection:
            conn.close()


def record_review(flashcard_id: int, grade: Grade, conn: sqlite3.Connection | None = None) -> None:
    """Apply a review grade to a flashcard and persist the resulting FSRS state."""
    owns_connection = conn is None
    if conn is None:
        conn = get_connection()
    try:
        now = _now()
        row = conn.execute(
            "SELECT stability, difficulty, last_reviewed_at, review_count "
            "FROM review_state WHERE flashcard_id = ?",
            (flashcard_id,),
        ).fetchone()

        if row is None:
            state = ReviewState(stability=0.0, difficulty=0.0, review_count=0)
            last_reviewed_at = None
        else:
            state = ReviewState(
                stability=row["stability"],
                difficulty=row["difficulty"],
                review_count=row["review_count"],
            )
            last_reviewed_at = _parse_timestamp(row["last_reviewed_at"])

        result = fsrs_review(state, grade, now=now, last_reviewed_at=last_reviewed_at)

        conn.execute(
            """
            INSERT INTO review_state
                (flashcard_id, stability, difficulty, due_date, last_reviewed_at, review_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(flashcard_id) DO UPDATE SET
                stability = excluded.stability,
                difficulty = excluded.difficulty,
                due_date = excluded.due_date,
                last_reviewed_at = excluded.last_reviewed_at,
                review_count = excluded.review_count
            """,
            (
                flashcard_id,
                result.stability,
                result.difficulty,
                result.due_date.isoformat(),
                now.isoformat(),
                result.review_count,
            ),
        )
        conn.commit()
    finally:
        if owns_connection:
            conn.close()
