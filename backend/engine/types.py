from dataclasses import dataclass
from typing import Any, Literal, Protocol

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True)
class CompletionResult:
    text: str
    model: str


class Engine(Protocol):
    async def complete(self, messages: list[Message]) -> CompletionResult: ...

    async def structured(
        self, messages: list[Message], schema: dict[str, Any]
    ) -> dict[str, Any]: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...
