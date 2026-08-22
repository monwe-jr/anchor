from dataclasses import dataclass, field
from typing import Any, Literal

SourceType = Literal["text", "pdf", "docx", "url"]


@dataclass(frozen=True)
class IngestResult:
    text: str
    source_type: SourceType
    source_name: str
    metadata: dict[str, Any] = field(default_factory=dict)
