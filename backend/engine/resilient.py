import asyncio
import random
from typing import Any, Awaitable, Callable, TypeVar

import httpx

from engine.types import CompletionResult, Engine, Message

T = TypeVar("T")

_TRANSIENT_STATUS_CODES = {429}


def _is_transient(exc: Exception) -> bool:
    if isinstance(
        exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException)
    ):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _TRANSIENT_STATUS_CODES
    return False


class ResilientEngine:
    def __init__(self, engine: Engine, max_retries: int = 3, base_delay: float = 0.5) -> None:
        self._engine = engine
        self._max_retries = max_retries
        self._base_delay = base_delay

    async def _call_with_retry(self, fn: Callable[..., Awaitable[T]], *args: Any) -> T:
        attempt = 0
        while True:
            try:
                return await fn(*args)
            except Exception as exc:
                if not _is_transient(exc) or attempt >= self._max_retries:
                    raise
                delay = self._base_delay * (2**attempt) + random.uniform(0, self._base_delay)
                await asyncio.sleep(delay)
                attempt += 1

    async def complete(self, messages: list[Message]) -> CompletionResult:
        return await self._call_with_retry(self._engine.complete, messages)

    async def structured(
        self, messages: list[Message], schema: dict[str, Any]
    ) -> dict[str, Any]:
        return await self._call_with_retry(self._engine.structured, messages, schema)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self._call_with_retry(self._engine.embed, texts)


def resilient(engine: Engine, max_retries: int = 3, base_delay: float = 0.5) -> Engine:
    return ResilientEngine(engine, max_retries=max_retries, base_delay=base_delay)
