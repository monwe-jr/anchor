from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.ollama import OllamaEngine
from engine.resilient import resilient
from rag.chat import answer_question

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_engine = resilient(OllamaEngine())


@app.get("/health")
def health():
    return {"status": "ok"}


class ChatRequest(BaseModel):
    question: str
    document_id: int | None = None


class ChatCitation(BaseModel):
    chunk_id: int
    document_id: int
    chunk_index: int
    quote: str
    chunk_text: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[ChatCitation]


@app.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    result = await answer_question(request.question, _engine, document_id=request.document_id)
    return ChatResponse(
        answer=result.answer,
        citations=[
            ChatCitation(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                chunk_index=c.chunk_index,
                quote=c.quote,
                chunk_text=c.chunk_text,
            )
            for c in result.citations
        ],
    )