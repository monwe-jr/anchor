import sqlite3


def delete_document(conn: sqlite3.Connection, document_id: int) -> None:
    """Delete a document and every row that references it.

    The schema declares foreign keys (e.g. `chunks.document_id REFERENCES
    documents(id)`) without `ON DELETE CASCADE`, and SQLite has no `ALTER
    TABLE ... ADD CONSTRAINT` — adding cascade behavior to an existing
    foreign key means rebuilding the table (create a new table with the
    constraint, copy rows, drop the old one, rename). That's a real
    migration, and this project already has a populated `anchor.db` on
    disk, so it's not something to do implicitly on every startup.

    Instead we delete the dependent rows explicitly, children before
    parents, in a single transaction the caller commits or rolls back as a
    unit. This is all-or-nothing without requiring any schema migration,
    and `PRAGMA foreign_keys = ON` (set in `get_connection`) still protects
    against a bug here: deleting a parent row out of order would raise an
    `IntegrityError` instead of silently orphaning rows.
    """
    conn.execute(
        "DELETE FROM quiz_attempts WHERE question_id IN "
        "(SELECT id FROM quiz_questions WHERE document_id = ?)",
        (document_id,),
    )
    conn.execute("DELETE FROM quiz_questions WHERE document_id = ?", (document_id,))
    conn.execute(
        "DELETE FROM review_state WHERE flashcard_id IN "
        "(SELECT id FROM flashcards WHERE document_id = ?)",
        (document_id,),
    )
    conn.execute("DELETE FROM flashcards WHERE document_id = ?", (document_id,))
    conn.execute("DELETE FROM notes WHERE document_id = ?", (document_id,))
    conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
    conn.execute("DELETE FROM jobs WHERE document_id = ?", (document_id,))
    conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))


def rename_document(conn: sqlite3.Connection, document_id: int, display_name: str) -> None:
    """Set a document's display name without touching `source_name`.

    `source_name` is the original filename/path/URL the document was
    ingested from. Overwriting it on rename would destroy that
    provenance — there'd be no way to tell what file a renamed document
    actually came from, which matters for re-ingesting, debugging, or
    just remembering where something was sourced from. Keeping
    `display_name` as a separate nullable column lets the user's chosen
    title live independently, while `source_name` stays intact as the
    permanent record. Reads fall back to `source_name` via `COALESCE`
    when no display name has been set.
    """
    conn.execute(
        "UPDATE documents SET display_name = ? WHERE id = ?", (display_name, document_id)
    )
