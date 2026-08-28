import sqlite3

import pytest

from db.schema import init_db
from documents.service import delete_document, rename_document


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    init_db(connection)
    yield connection
    connection.close()


def _seed_document(conn: sqlite3.Connection, source_name: str = "doc.txt") -> int:
    cursor = conn.execute(
        "INSERT INTO documents (source_name, source_type, full_text, created_at) "
        "VALUES (?, 'text', 'body', '2026-01-01T00:00:00+00:00')",
        (source_name,),
    )
    document_id = cursor.lastrowid

    conn.execute(
        "INSERT INTO chunks (document_id, chunk_index, text, embedding) VALUES (?, 0, 'chunk', NULL)",
        (document_id,),
    )
    conn.execute(
        "INSERT INTO notes (document_id, content) VALUES (?, 'a note')", (document_id,)
    )
    flashcard_id = conn.execute(
        "INSERT INTO flashcards (document_id, question, answer) VALUES (?, 'Q', 'A')",
        (document_id,),
    ).lastrowid
    conn.execute(
        "INSERT INTO review_state (flashcard_id, stability, difficulty, due_date) "
        "VALUES (?, 1.0, 1.0, '2026-01-01T00:00:00+00:00')",
        (flashcard_id,),
    )
    question_id = conn.execute(
        "INSERT INTO quiz_questions (document_id, question, options, correct_option_index, topic, difficulty) "
        "VALUES (?, 'Q?', '[\"a\",\"b\"]', 0, 'Topic', 'beginner')",
        (document_id,),
    ).lastrowid
    conn.execute(
        "INSERT INTO quiz_attempts (question_id, chosen_option_index, correct, answered_at) "
        "VALUES (?, 0, 1, '2026-01-01T00:00:00+00:00')",
        (question_id,),
    )
    conn.execute(
        "INSERT INTO jobs (document_id, status, current_stage, error_message, created_at, updated_at) "
        "VALUES (?, 'done', NULL, NULL, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00')",
        (document_id,),
    )
    conn.commit()
    return document_id


def test_delete_document_removes_all_related_rows(conn):
    document_id = _seed_document(conn)

    delete_document(conn, document_id)
    conn.commit()

    assert conn.execute("SELECT COUNT(*) FROM documents WHERE id = ?", (document_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM chunks WHERE document_id = ?", (document_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM notes WHERE document_id = ?", (document_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM flashcards WHERE document_id = ?", (document_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM review_state").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM quiz_questions WHERE document_id = ?", (document_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM quiz_attempts").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM jobs WHERE document_id = ?", (document_id,)).fetchone()[0] == 0


def test_delete_document_does_not_affect_other_documents(conn):
    keep_id = _seed_document(conn, source_name="keep.txt")
    delete_id = _seed_document(conn, source_name="delete.txt")

    delete_document(conn, delete_id)
    conn.commit()

    assert conn.execute("SELECT COUNT(*) FROM documents WHERE id = ?", (keep_id,)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM chunks WHERE document_id = ?", (keep_id,)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM notes WHERE document_id = ?", (keep_id,)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM flashcards WHERE document_id = ?", (keep_id,)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM quiz_questions WHERE document_id = ?", (keep_id,)).fetchone()[0] == 1


def test_delete_document_order_satisfies_foreign_key_constraints(conn):
    """Deleting children before parents must not trip PRAGMA foreign_keys = ON.

    This is the behavior the explicit-order approach exists to get right:
    with foreign keys enforced, deleting a parent row while a child still
    references it raises IntegrityError. If delete_document ever regresses
    to the wrong order, this test fails with that error.
    """
    document_id = _seed_document(conn)

    delete_document(conn, document_id)
    conn.commit()  # would have raised sqlite3.IntegrityError on a bad order


def test_rename_document_sets_display_name_without_touching_source_name(conn):
    document_id = _seed_document(conn, source_name="original-file.pdf")

    rename_document(conn, document_id, "My Renamed Title")
    conn.commit()

    row = conn.execute(
        "SELECT source_name, display_name FROM documents WHERE id = ?", (document_id,)
    ).fetchone()
    assert row["display_name"] == "My Renamed Title"
    assert row["source_name"] == "original-file.pdf"


def test_rename_document_can_be_applied_more_than_once(conn):
    document_id = _seed_document(conn)

    rename_document(conn, document_id, "First Title")
    rename_document(conn, document_id, "Second Title")
    conn.commit()

    row = conn.execute("SELECT display_name FROM documents WHERE id = ?", (document_id,)).fetchone()
    assert row["display_name"] == "Second Title"
