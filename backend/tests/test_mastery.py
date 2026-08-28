import json
import sqlite3
from datetime import datetime, timezone

import pytest

from db.schema import init_db
from study.mastery import compute_mastery


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    init_db(connection)
    yield connection
    connection.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _seed_document(conn: sqlite3.Connection) -> int:
    cursor = conn.execute(
        "INSERT INTO documents (source_name, source_type, full_text, created_at) VALUES (?, ?, ?, ?)",
        ("bio-notes", "text", "some text", _now()),
    )
    conn.commit()
    return cursor.lastrowid


def _seed_question(conn: sqlite3.Connection, document_id: int, topic: str, correct_option_index: int) -> int:
    cursor = conn.execute(
        "INSERT INTO quiz_questions "
        "(document_id, question, options, correct_option_index, topic, difficulty) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (document_id, "Q?", json.dumps(["A", "B", "C", "D"]), correct_option_index, topic, "intermediate"),
    )
    conn.commit()
    return cursor.lastrowid


def _record_attempt(conn: sqlite3.Connection, question_id: int, chosen_option_index: int, correct: bool) -> None:
    conn.execute(
        "INSERT INTO quiz_attempts (question_id, chosen_option_index, correct, answered_at) "
        "VALUES (?, ?, ?, ?)",
        (question_id, chosen_option_index, correct, _now()),
    )
    conn.commit()


def test_compute_mastery_groups_by_topic_and_computes_percent_correct(conn):
    document_id = _seed_document(conn)
    photo_q1 = _seed_question(conn, document_id, "Photosynthesis", correct_option_index=0)
    photo_q2 = _seed_question(conn, document_id, "Photosynthesis", correct_option_index=1)
    resp_q1 = _seed_question(conn, document_id, "Respiration", correct_option_index=2)

    _record_attempt(conn, photo_q1, chosen_option_index=0, correct=True)
    _record_attempt(conn, photo_q1, chosen_option_index=1, correct=False)
    _record_attempt(conn, photo_q2, chosen_option_index=1, correct=True)
    _record_attempt(conn, resp_q1, chosen_option_index=2, correct=True)
    _record_attempt(conn, resp_q1, chosen_option_index=0, correct=False)

    mastery = compute_mastery(document_id, conn=conn)
    by_topic = {m.topic: m for m in mastery}

    assert set(by_topic) == {"Photosynthesis", "Respiration"}

    assert by_topic["Photosynthesis"].total_attempts == 3
    assert by_topic["Photosynthesis"].correct_attempts == 2
    assert by_topic["Photosynthesis"].mastery_percent == pytest.approx(66.7, abs=0.1)

    assert by_topic["Respiration"].total_attempts == 2
    assert by_topic["Respiration"].correct_attempts == 1
    assert by_topic["Respiration"].mastery_percent == 50.0


def test_compute_mastery_excludes_topics_with_no_attempts(conn):
    document_id = _seed_document(conn)
    _seed_question(conn, document_id, "Untouched Topic", correct_option_index=0)

    mastery = compute_mastery(document_id, conn=conn)

    assert mastery == []


def test_compute_mastery_scopes_to_the_requested_document(conn):
    document_id_a = _seed_document(conn)
    document_id_b = _seed_document(conn)
    q_a = _seed_question(conn, document_id_a, "Topic", correct_option_index=0)
    q_b = _seed_question(conn, document_id_b, "Topic", correct_option_index=0)

    _record_attempt(conn, q_a, chosen_option_index=0, correct=True)
    _record_attempt(conn, q_b, chosen_option_index=1, correct=False)

    mastery_a = compute_mastery(document_id_a, conn=conn)

    assert len(mastery_a) == 1
    assert mastery_a[0].total_attempts == 1
    assert mastery_a[0].correct_attempts == 1
    assert mastery_a[0].mastery_percent == 100.0
