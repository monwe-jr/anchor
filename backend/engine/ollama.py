import json
from typing import Any

import httpx

from engine.types import CompletionResult, Message

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_CHAT_MODEL = "llama3.1:8b"
DEFAULT_EMBED_MODEL = "nomic-embed-text"


class OllamaEngine:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        chat_model: str = DEFAULT_CHAT_MODEL,
        embed_model: str = DEFAULT_EMBED_MODEL,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._chat_model = chat_model
        self._embed_model = embed_model
        self._client = client or httpx.AsyncClient(timeout=120.0)

    async def complete(self, messages: list[Message]) -> CompletionResult:
        response = await self._client.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._chat_model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()
        return CompletionResult(text=data["message"]["content"], model=self._chat_model)

    async def structured(
        self, messages: list[Message], schema: dict[str, Any]
    ) -> dict[str, Any]:
        response = await self._client.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._chat_model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "format": schema,
                "stream": False,
            },
        )
        response.raise_for_status()
        data = response.json()
        return json.loads(data["message"]["content"])

    async def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        for text in texts:
            response = await self._client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._embed_model, "prompt": text},
            )
            response.raise_for_status()
            embeddings.append(response.json()["embedding"])
        return embeddings
