from typing import Any

import httpx
import pytest

from engine.resilient import resilient
from engine.types import CompletionResult, Message

SOME_MESSAGES = [Message(role="user", content="hi")]


class FlakyThenSucceedsEngine:
    """Fails with a transient error `fail_times` times, then succeeds."""

    def __init__(self, fail_times: int) -> None:
        self._fail_times = fail_times
        self.calls = 0

    async def complete(self, messages: list[Message]) -> CompletionResult:
        self.calls += 1
        if self.calls <= self._fail_times:
            raise httpx.ConnectError("simulated connection failure")
        return CompletionResult(text="ok", model="fake")

    async def structured(self, messages: list[Message], schema: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class AlwaysFailsEngine:
    """Always fails with a transient error."""

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, messages: list[Message]) -> CompletionResult:
        self.calls += 1
        raise httpx.ConnectError("simulated connection failure")

    async def structured(self, messages: list[Message], schema: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    async def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


async def test_retries_and_recovers_from_transient_failures():
    fake = FlakyThenSucceedsEngine(fail_times=2)
    engine = resilient(fake, max_retries=3, base_delay=0.01)

    result = await engine.complete(SOME_MESSAGES)

    assert result == CompletionResult(text="ok", model="fake")
    assert fake.calls == 3  # 2 failures + 1 success


async def test_gives_up_after_max_retries_instead_of_retrying_forever():
    fake = AlwaysFailsEngine()
    engine = resilient(fake, max_retries=2, base_delay=0.01)

    with pytest.raises(httpx.ConnectError):
        await engine.complete(SOME_MESSAGES)

    assert fake.calls == 3  # 1 initial attempt + 2 retries, then it gives up
