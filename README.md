# Anchor

A local-first study tool that turns your own documents into notes, spaced-repetition flashcards, quizzes, and a citation-grounded chat — all running against a local LLM via [Ollama](https://ollama.com), with no data ever leaving your machine.

## Why this exists

I built Anchor to go deep on a few things I wanted to actually understand rather than just read about: provider-agnostic AI abstractions, retrieval-augmented generation with real citation grounding, and the FSRS spaced-repetition algorithm. The architecture was inspired by patterns I studied in other local-first study-tool projects (particularly the engine/ingest/pipeline separation), but every line of code here is my own implementation, written from scratch and tested independently.

## Features

- **Ingest anything** — plain text, PDF, DOCX, or a URL, normalized into a consistent shape before anything downstream touches it
- **Auto-generated notes and flashcards** from ingested content, via a resumable generation pipeline with per-stage progress tracking
- **Spaced repetition review** using a clean-room implementation of FSRS (Free Spaced Repetition Scheduler) — review intervals are computed from an actual forgetting-curve model, not a fixed schedule
- **Multiple-choice quizzes** generated per document, with per-topic mastery tracked across attempts over time
- **Chat with your documents** — retrieval-augmented answers grounded *only* in your ingested content, with every claim traceable back to the exact source chunk it came from
- **Fully local** — chat, embeddings, and generation all run through Ollama; nothing is sent to a third-party API

## Architecture

The backend is organized around a few deliberate boundaries:

```
backend/
├── engine/       # Provider-agnostic AI interface (Protocol) + Ollama implementation
├── ingest/       # Normalizes text/PDF/DOCX/URL into one consistent shape
├── generation/   # Chunking + the ingest → embed → generate → persist pipeline
├── rag/          # Retrieval (cosine similarity) + citation-grounded chat
├── study/        # FSRS spaced repetition (pure functions) + DB-facing scheduler
├── db/           # SQLite schema
└── main.py       # FastAPI routes
```

**Engine abstraction.** `engine/types.py` defines an `Engine` Protocol (`complete`, `structured`, `embed`) that any AI provider can satisfy structurally, without inheritance. `engine/ollama.py` implements it against Ollama's local HTTP API. `engine/resilient.py` wraps any `Engine` with exponential-backoff retry on transient failures — a decorator that takes an `Engine` and returns something that still satisfies `Engine`, so the rest of the app never knows or cares whether it's talking to a raw or a wrapped instance.

**Ingest normalization.** Four source types (text, PDF, DOCX, URL) all funnel through a single `ingest()` dispatcher into one `IngestResult` shape, so nothing downstream ever branches on where the content came from.

**Generation pipeline.** Each stage (chunk → embed → generate) writes its status to a `jobs` row as it progresses, so a crash mid-run leaves a resumable, inspectable record instead of silent data loss — trading a small amount of write overhead for real crash visibility.

**RAG with grounding.** Chat retrieval computes cosine similarity between a query embedding and stored chunk embeddings in plain Python — deliberately no vector database, since the dataset size here doesn't warrant one. The chat prompt explicitly instructs the model to answer only from retrieved chunks, and requests structured output (not free-text with regex-parsed citations) so citations reliably map back to real chunk IDs.

**FSRS.** The scheduling math (`study/fsrs.py`) is implemented as pure functions with no database access, separated from the DB-facing scheduler (`study/scheduler.py`) that calls it. Pure functions are trivial to test in isolation; the DB layer is a thin, separately-tested wrapper around them.

## Tech stack

- **Backend:** Python, FastAPI, SQLite, httpx
- **Frontend:** Next.js, TypeScript, Tailwind CSS
- **AI:** Ollama (local), using a chat model and `nomic-embed-text` for embeddings
- **Testing:** pytest, pytest-asyncio

## Getting started

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.com/download) installed and running

### 1. Pull the models

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`.

### Running tests

```bash
cd backend
source venv/bin/activate
pytest -v
```

## Design decisions worth highlighting

- **Structural typing (`Protocol`) over inheritance (`ABC`)** for the engine interface — any provider that matches the method shape satisfies it, no forced base class.
- **Cosine similarity over a vector database** — at this project's scale, brute-force comparison in Python is simpler, has no extra infrastructure dependency, and is fast enough; a real vector store would be the right call at a much larger corpus size.
- **Structured output over regex-parsed citations** — asking the model for a typed JSON schema is far more reliable than parsing citation markers out of free-form text.
- **Per-stage job persistence over end-of-run persistence** — writing progress after every pipeline stage means a crash leaves a debuggable, resumable record instead of nothing.
- **A startup recovery step** marks any job left in a non-terminal state (from a crash or restart) as failed, so orphaned "processing" records can't silently persist forever.

## Known limitations / possible next steps

- Vector search is brute-force in-process; would need a real vector index at larger scale
- No user auth — single-user, local-only by design
- No audio/YouTube ingestion yet (text, PDF, DOCX, and URL only)

## Acknowledgments

The engine/ingest/pipeline architectural pattern was inspired by studying other local-first AI study-tool projects. No code from any other project is reused here — this is an independent, from-scratch implementation built specifically to learn the underlying patterns firsthand.