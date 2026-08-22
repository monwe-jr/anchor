from typing import Any

from ingest.normalizers import from_docx, from_pdf, from_text, from_url
from ingest.types import IngestResult, SourceType

_DISPATCH = {
    "text": lambda source: from_text(source, "text"),
    "pdf": from_pdf,
    "docx": from_docx,
    "url": from_url,
}


def ingest(source: Any, source_type: str) -> IngestResult:
    normalizer = _DISPATCH.get(source_type)
    if normalizer is None:
        supported = ", ".join(sorted(_DISPATCH))
        raise ValueError(f"Unsupported source_type {source_type!r}. Supported types: {supported}")

    return normalizer(source)


__all__ = ["ingest", "IngestResult", "SourceType"]
