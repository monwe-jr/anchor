import sqlite3

from db.schema import init_db


def test_init_db_is_idempotent_and_creates_display_name_column():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        init_db(conn)  # calling twice must not raise

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
        assert "display_name" in columns
    finally:
        conn.close()


def test_init_db_adds_display_name_to_a_pre_existing_documents_table():
    """Simulates a database created before display_name existed."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """
            CREATE TABLE documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                full_text TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO documents (source_name, source_type, full_text, created_at) "
            "VALUES ('old.txt', 'text', 'body', '2026-01-01T00:00:00+00:00')"
        )
        conn.commit()

        init_db(conn)

        columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
        assert "display_name" in columns

        row = conn.execute("SELECT source_name, display_name FROM documents").fetchone()
        assert row["source_name"] == "old.txt"
        assert row["display_name"] is None
    finally:
        conn.close()
