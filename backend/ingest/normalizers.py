import httpx
from bs4 import BeautifulSoup
from docx import Document
from pypdf import PdfReader

from ingest.types import IngestResult


def from_text(raw: str, name: str) -> IngestResult:
    return IngestResult(
        text=raw,
        source_type="text",
        source_name=name,
        metadata={"char_count": len(raw)},
    )


def from_pdf(file_path: str) -> IngestResult:
    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages)
    return IngestResult(
        text=text,
        source_type="pdf",
        source_name=file_path,
        metadata={"page_count": len(reader.pages), "char_count": len(text)},
    )


def from_docx(file_path: str) -> IngestResult:
    document = Document(file_path)
    paragraphs = [p.text for p in document.paragraphs if p.text]
    text = "\n".join(paragraphs)
    return IngestResult(
        text=text,
        source_type="docx",
        source_name=file_path,
        metadata={"paragraph_count": len(paragraphs), "char_count": len(text)},
    )


def from_url(url: str) -> IngestResult:
    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    return IngestResult(
        text=text,
        source_type="url",
        source_name=url,
        metadata={
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "char_count": len(text),
        },
    )
