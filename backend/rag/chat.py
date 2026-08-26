"""Grounded question-answering over retrieved chunks (retrieval.py) via the Engine protocol."""

import sqlite3
from dataclasses import dataclass

from engine.types import Engine, Message
from rag.retrieval import RetrievedChunk, retrieve_relevant_chunks

CITATION_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "chunk_id": {"type": "integer"},
                    "quote": {"type": "string"},
                },
                "required": ["chunk_id", "quote"],
            },
        },
    },
    "required": ["answer", "citations"],
}

_SYSTEM_PROMPT = (
    "You answer questions using ONLY the numbered chunks of source text provided below. Do not "
    "introduce facts, entities, or details that are not stated in the chunks. Questions are often "
    "phrased with different words than the chunks use for the same concept - treat that as a "
    "wording difference, not a reason to refuse. For example, if a chunk states that a process "
    "'produces glucose', a question asking how the process 'produces energy' is asking about the "
    "same thing, since glucose is a form of energy - answer it using the chunk, don't refuse it.\n\n"
    "Every factual claim in your answer must be supported by at least one chunk. In the "
    "citations list, cite the number of each chunk that supports a claim and quote the exact "
    "supporting text from that chunk. Do not invent chunk numbers or quotes that are not "
    "actually present below.\n\n"
    "Only say the documents don't contain the information if the underlying concept the question "
    "asks about is genuinely absent from every chunk - not merely phrased differently."
)


@dataclass(frozen=True)
class Citation:
    chunk_id: int
    quote: str
    document_id: int
    chunk_index: int
    chunk_text: str


@dataclass(frozen=True)
class AnswerResult:
    answer: str
    citations: list[Citation]
    retrieved_chunks: list[RetrievedChunk]


def _build_messages(query: str, chunks: list[RetrievedChunk]) -> list[Message]:
    numbered = "\n\n".join(f"Chunk {i + 1}:\n{chunk.text}" for i, chunk in enumerate(chunks))
    return [
        Message(role="system", content=_SYSTEM_PROMPT),
        Message(role="user", content=f"{numbered}\n\nQuestion: {query}"),
    ]


def _resolve_citations(raw_citations: list[dict], chunks: list[RetrievedChunk]) -> list[Citation]:
    resolved = []
    for raw in raw_citations:
        # The model cites chunks by the 1-based ordinal we showed it in the prompt, not a
        # real chunk_id, so this is a lookup into the *actually retrieved* set - not a
        # trusted foreign key. Anything out of range is a hallucinated citation and is dropped.
        ordinal = raw.get("chunk_id")
        if not isinstance(ordinal, int) or not (1 <= ordinal <= len(chunks)):
            continue
        chunk = chunks[ordinal - 1]
        resolved.append(
            Citation(
                chunk_id=chunk.chunk_id,
                quote=raw.get("quote", ""),
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.text,
            )
        )
    return resolved


async def answer_question(
    query: str,
    engine: Engine,
    document_id: int | None = None,
    top_k: int = 5,
    conn: sqlite3.Connection | None = None,
) -> AnswerResult:
    chunks = await retrieve_relevant_chunks(
        query, engine, document_id=document_id, top_k=top_k, conn=conn
    )

    if not chunks:
        return AnswerResult(
            answer="There are no ingested documents to answer this question from.",
            citations=[],
            retrieved_chunks=[],
        )

    messages = _build_messages(query, chunks)
    result = await engine.structured(messages, CITATION_SCHEMA)

    return AnswerResult(
        answer=result.get("answer", ""),
        citations=_resolve_citations(result.get("citations", []), chunks),
        retrieved_chunks=chunks,
    )
