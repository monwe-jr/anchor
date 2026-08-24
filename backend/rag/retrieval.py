"""Embedding-similarity retrieval over chunks already stored by generation/pipeline.py."""

import json
import math
import sqlite3
from dataclasses import dataclass

from db.schema import get_connection
from engine.types import Engine


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: int
    document_id: int
    chunk_index: int
    text: str
    similarity: float


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


async def retrieve_relevant_chunks(
    query: str,
    engine: Engine,
    document_id: int | None = None,
    top_k: int = 5,
    conn: sqlite3.Connection | None = None,
) -> list[RetrievedChunk]:
    """Embed `query`, score it against stored chunk embeddings by cosine similarity,
    and return the top_k chunks (optionally scoped to one document)."""
    owns_connection = conn is None
    if conn is None:
        conn = get_connection()
    try:
        query_embedding = (await engine.embed([query]))[0]

        if document_id is None:
            rows = conn.execute(
                "SELECT id, document_id, chunk_index, text, embedding "
                "FROM chunks WHERE embedding IS NOT NULL"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, document_id, chunk_index, text, embedding "
                "FROM chunks WHERE document_id = ? AND embedding IS NOT NULL",
                (document_id,),
            ).fetchall()

        scored = [
            RetrievedChunk(
                chunk_id=row["id"],
                document_id=row["document_id"],
                chunk_index=row["chunk_index"],
                text=row["text"],
                similarity=_cosine_similarity(query_embedding, json.loads(row["embedding"])),
            )
            for row in rows
        ]
        scored.sort(key=lambda c: c.similarity, reverse=True)
        return scored[:top_k]
    finally:
        if owns_connection:
            conn.close()
