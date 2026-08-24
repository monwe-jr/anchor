import json
import sqlite3
from typing import Any

import pytest

from db.schema import init_db
from engine.types import CompletionResult, Message
from rag.chat import answer_question
from rag.retrieval import retrieve_relevant_chunks


class FakeEngine:
    """Canned Engine: returns a fixed embedding for any embed() call and a fixed
    structured() response, so retrieval ranking and citation resolution are
    driven entirely by hand-crafted DB state, not by real model behavior."""

    def __init__(self, query_embedding=None, structured_response=None) -> None:
        self.embed_calls: list[list[str]] = []
        self.structured_calls: list[tuple[list[Message], dict[str, Any]]] = []
        self._query_embedding = query_embedding if query_embedding is not None else [1.0, 0.0]
        self._structured_response = (
            structured_response if structured_response is not None else {"answer": "", "citations": []}
        )

    async def complete(self, messages: list[Message]) -> CompletionResult:
        raise NotImplementedError

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.embed_calls.append(texts)
        return [self._query_embedding for _ in texts]

    async def structured(self, messages: list[Message], schema: dict[str, Any]) -> dict[str, Any]:
        self.structured_calls.append((messages, schema))
        return self._structured_response


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    init_db(connection)
    yield connection
    connection.close()


def _insert_document(conn: sqlite3.Connection) -> int:
    cursor = conn.execute(
        "INSERT INTO documents (source_name, source_type, full_text, created_at) VALUES (?, ?, ?, ?)",
        ("doc", "text", "full text", "2026-01-01T00:00:00+00:00"),
    )
    conn.commit()
    return cursor.lastrowid


def _insert_chunk(
    conn: sqlite3.Connection, document_id: int, chunk_index: int, text: str, embedding: list[float]
) -> int:
    cursor = conn.execute(
        "INSERT INTO chunks (document_id, chunk_index, text, embedding) VALUES (?, ?, ?, ?)",
        (document_id, chunk_index, text, json.dumps(embedding)),
    )
    conn.commit()
    return cursor.lastrowid


async def test_retrieve_relevant_chunks_ranks_by_cosine_similarity(conn):
    document_id = _insert_document(conn)
    # Hand-crafted so the correct ranking is known ahead of time: [1,0] is a
    # perfect match for the query embedding, [0.9,0.1] is a close second, and
    # [0,1] is orthogonal (zero similarity) - not something random vectors guarantee.
    _insert_chunk(conn, document_id, 0, "cats are mammals", [1.0, 0.0])
    _insert_chunk(conn, document_id, 1, "the stock market rose today", [0.0, 1.0])
    _insert_chunk(conn, document_id, 2, "kittens are baby cats", [0.9, 0.1])

    engine = FakeEngine(query_embedding=[1.0, 0.0])

    results = await retrieve_relevant_chunks("tell me about cats", engine, top_k=3, conn=conn)

    assert [r.text for r in results] == [
        "cats are mammals",
        "kittens are baby cats",
        "the stock market rose today",
    ]
    assert results[0].similarity > results[1].similarity > results[2].similarity
    assert results[0].similarity == pytest.approx(1.0)
    assert results[2].similarity == pytest.approx(0.0)


async def test_retrieve_relevant_chunks_respects_top_k(conn):
    document_id = _insert_document(conn)
    for i in range(5):
        _insert_chunk(conn, document_id, i, f"chunk {i}", [1.0, 0.0])

    engine = FakeEngine(query_embedding=[1.0, 0.0])

    results = await retrieve_relevant_chunks("query", engine, top_k=2, conn=conn)

    assert len(results) == 2


async def test_answer_question_resolves_citations_to_real_chunk_text(conn):
    document_id = _insert_document(conn)
    _insert_chunk(conn, document_id, 0, "The Eiffel Tower is in Paris.", [1.0, 0.0])
    _insert_chunk(conn, document_id, 1, "Unrelated chunk about weather.", [0.0, 1.0])
    real_chunk_id = conn.execute(
        "SELECT id FROM chunks WHERE text = ?", ("The Eiffel Tower is in Paris.",)
    ).fetchone()["id"]

    structured_response = {
        "answer": "The Eiffel Tower is located in Paris.",
        # The model cites the 1-based *ordinal* it was shown in the prompt ("Chunk 1"),
        # not the real DB id - that's the whole point of the resolution step below.
        "citations": [{"chunk_id": 1, "quote": "The Eiffel Tower is in Paris."}],
    }
    engine = FakeEngine(query_embedding=[1.0, 0.0], structured_response=structured_response)

    result = await answer_question("Where is the Eiffel Tower?", engine, conn=conn)

    assert result.answer == "The Eiffel Tower is located in Paris."
    assert len(result.citations) == 1
    citation = result.citations[0]
    assert citation.chunk_id == real_chunk_id
    assert citation.chunk_text == "The Eiffel Tower is in Paris."
    assert citation.document_id == document_id
    assert citation.chunk_index == 0


async def test_answer_question_drops_hallucinated_citations(conn):
    document_id = _insert_document(conn)
    _insert_chunk(conn, document_id, 0, "Only one real chunk here.", [1.0, 0.0])

    structured_response = {
        "answer": "Some answer.",
        "citations": [{"chunk_id": 99, "quote": "a quote that was never shown to the model"}],
    }
    engine = FakeEngine(query_embedding=[1.0, 0.0], structured_response=structured_response)

    result = await answer_question("A question", engine, conn=conn)

    assert result.citations == []


async def test_answer_question_hedges_when_no_chunks_exist(conn):
    engine = FakeEngine(query_embedding=[1.0, 0.0])

    result = await answer_question("Anything?", engine, conn=conn)

    assert result.citations == []
    assert engine.structured_calls == []  # model is never called with no grounding available
