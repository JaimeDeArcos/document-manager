"""Extract page-aware, section-aware text from selectable-text PDFs."""

from hashlib import sha256
import re

import pymupdf
import pymupdf4llm

from .models import Chunk


HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
IMAGE_MARKER = re.compile(r"^(?:!\[.*?\]\(.*?\)|==> picture .*<==)$")
MAX_CHARS = 1200
OVERLAP = 150


def split_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP) -> list[str]:
    """Make bounded chunks, preferring paragraph and word boundaries."""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    result = []
    while len(text) > max_chars:
        cut = text.rfind("\n\n", 0, max_chars)
        if cut < max_chars // 2:
            cut = text.rfind(" ", 0, max_chars)
        if cut < max_chars // 2:
            cut = max_chars
        result.append(text[:cut].strip())
        text = text[max(cut - overlap, 0) :].lstrip()
    if text:
        result.append(text)
    return result


def chunks_from_pages(pages: list[dict], filename: str, file_hash: str) -> list[Chunk]:
    """Keep the most recent heading or PDF TOC entry as a section label."""
    result: list[Chunk] = []
    current_section = ""

    for page in pages:
        page_number = int(page["metadata"]["page"])
        for toc_item in page.get("toc_items", []):
            current_section = str(toc_item[1]).strip() or current_section

        section = current_section or f"Page {page_number}"
        body: list[str] = []

        def flush() -> None:
            nonlocal body
            for text in split_text("\n".join(body)):
                digest = sha256(
                    f"{filename}\0{file_hash}\0{page_number}\0{section}\0{text}".encode()
                ).hexdigest()
                result.append(Chunk(digest, text, filename, page_number, section, file_hash))
            body = []

        for line in str(page.get("text", "")).splitlines():
            line = line.strip()
            if not line or IMAGE_MARKER.match(line):
                if body and body[-1] != "":
                    body.append("")
                continue
            heading = HEADING.match(line)
            if heading:
                flush()
                section = heading.group(1).strip()
                current_section = section
            else:
                body.append(line)
        flush()

    return result


def extract_chunks(pdf_bytes: bytes, filename: str) -> tuple[str, list[Chunk]]:
    """Extract a PDF without OCR; return its hash and chunks."""
    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("This file is not a valid PDF.")

    file_hash = sha256(pdf_bytes).hexdigest()
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            if document.needs_pass:
                raise ValueError("Password-protected PDFs are not supported in Part 1.")
            if not any(page.get_text().strip() for page in document):
                raise ValueError("No selectable text found. Scanned PDFs need OCR, which is planned for Part 3.")
            pages = pymupdf4llm.to_markdown(document, page_chunks=True)
    except pymupdf.FileDataError as exc:
        raise ValueError("This PDF could not be read.") from exc

    chunks = chunks_from_pages(pages, filename, file_hash)
    if not chunks:
        raise ValueError("No usable text found in this PDF.")
    return file_hash, chunks
