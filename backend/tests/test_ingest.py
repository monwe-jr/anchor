from unittest.mock import Mock

import httpx
import pytest
from docx import Document
from reportlab.pdfgen import canvas

from ingest import ingest
from ingest.normalizers import from_docx, from_pdf, from_text, from_url


def _make_test_pdf(tmp_path, text: str = "Hello from a test PDF.") -> str:
    path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(100, 750, text)
    c.save()
    return str(path)


def _make_test_docx(tmp_path, paragraphs: list[str]) -> str:
    path = tmp_path / "sample.docx"
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    document.save(str(path))
    return str(path)


def test_from_text_returns_consistent_ingest_result():
    result = from_text("hello world", "greeting")

    assert result.text == "hello world"
    assert result.source_type == "text"
    assert result.source_name == "greeting"
    assert result.metadata == {"char_count": len("hello world")}


def test_from_pdf_extracts_text_and_page_count(tmp_path):
    pdf_path = _make_test_pdf(tmp_path, "Hello from a test PDF.")

    result = from_pdf(pdf_path)

    assert "Hello from a test PDF." in result.text
    assert result.source_type == "pdf"
    assert result.source_name == pdf_path
    assert result.metadata["page_count"] == 1
    assert result.metadata["char_count"] == len(result.text)


def test_from_docx_extracts_paragraph_text(tmp_path):
    docx_path = _make_test_docx(tmp_path, ["First paragraph.", "Second paragraph."])

    result = from_docx(docx_path)

    assert result.text == "First paragraph.\nSecond paragraph."
    assert result.source_type == "docx"
    assert result.source_name == docx_path
    assert result.metadata["paragraph_count"] == 2
    assert result.metadata["char_count"] == len(result.text)


def test_from_url_strips_html_and_scripts(monkeypatch):
    html = """
    <html>
      <head><style>body { color: red; }</style></head>
      <body>
        <script>console.log("should not appear");</script>
        <h1>Title</h1>
        <p>Some readable paragraph text.</p>
      </body>
    </html>
    """
    fake_response = Mock(spec=httpx.Response)
    fake_response.text = html
    fake_response.status_code = 200
    fake_response.headers = {"content-type": "text/html"}
    fake_response.raise_for_status = Mock()

    mock_get = Mock(return_value=fake_response)
    monkeypatch.setattr(httpx, "get", mock_get)

    result = from_url("https://example.com/article")

    assert "Title" in result.text
    assert "Some readable paragraph text." in result.text
    assert "should not appear" not in result.text
    assert "color: red" not in result.text
    assert result.source_type == "url"
    assert result.source_name == "https://example.com/article"
    assert result.metadata["status_code"] == 200
    assert result.metadata["content_type"] == "text/html"

    mock_get.assert_called_once_with(
        "https://example.com/article", timeout=30.0, follow_redirects=True
    )


def test_ingest_dispatches_by_source_type():
    result = ingest("plain text input", "text")

    assert result.source_type == "text"
    assert result.text == "plain text input"


def test_ingest_raises_clear_error_for_unsupported_type():
    with pytest.raises(ValueError, match="csv"):
        ingest("irrelevant", "csv")
