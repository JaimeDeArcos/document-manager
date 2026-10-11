import pymupdf
import pytest

from document_manager.pdf import extract_chunks, split_text


def test_extract_keeps_page_and_section():
    document = pymupdf.open()
    first = document.new_page()
    first.insert_text((72, 80), "Retention", fontsize=20)
    first.insert_text((72, 125), "Project notes are kept for 90 days.")
    second = document.new_page()
    second.insert_text((72, 80), "Deletion", fontsize=20)
    second.insert_text((72, 125), "The owner deletes the notes after retention.")
    document.set_toc([[1, "Retention", 1], [1, "Deletion", 2]])
    contents = document.tobytes()
    document.close()

    digest, chunks = extract_chunks(contents, "handbook.pdf")

    assert len(digest) == 64
    assert [(chunk.page, chunk.section) for chunk in chunks] == [
        (1, "Retention"), (2, "Deletion")
    ]
    assert "90 days" in chunks[0].text


def test_scanned_pdf_is_rejected_with_an_ocr_hint():
    document = pymupdf.open()
    document.new_page()
    contents = document.tobytes()
    document.close()

    with pytest.raises(ValueError, match="Scanned PDFs need OCR"):
        extract_chunks(contents, "scan.pdf")


def test_split_text_is_bounded_and_keeps_overlap():
    parts = split_text("alpha " * 400, max_chars=120, overlap=20)
    assert len(parts) > 2
    assert all(len(part) <= 120 for part in parts)
    assert "alpha" in parts[0] and "alpha" in parts[1]
