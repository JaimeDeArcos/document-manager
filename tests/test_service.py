import pymupdf

from document_manager.config import Settings
from document_manager.models import Answer
from document_manager.service import DocumentManager


class FakeModels:
    def embed(self, texts):
        return [[float(len(text)), 1.0] for text in texts]

    def answer(self, question, sources):
        return Answer("The cited excerpt says 90 days.", tuple(sources[:1]), True)


def pdf_bytes(body: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 80), "Retention", fontsize=20)
    page.insert_text((72, 125), body)
    document.set_toc([[1, "Retention", 1]])
    result = document.tobytes()
    document.close()
    return result


def test_upload_ask_replace_and_delete(tmp_path):
    settings = Settings(tmp_path / "data", "http://127.0.0.1:11434", "embed", "chat")
    manager = DocumentManager(settings, models=FakeModels())
    first = pdf_bytes("Project notes are kept for 90 days.")

    document, changed = manager.index_pdf("handbook.pdf", first)
    assert changed
    assert document.chunks == 1
    assert manager.pdf_path("handbook.pdf").read_bytes() == first
    assert manager.index_pdf("handbook.pdf", first)[1] is False
    answer = manager.ask("How long are notes kept?")
    assert answer.found
    assert (answer.sources[0].filename, answer.sources[0].page, answer.sources[0].section) == (
        "handbook.pdf", 1, "Retention"
    )

    updated = pdf_bytes("Project notes are kept for 30 days.")
    manager.index_pdf("handbook.pdf", updated)
    assert manager.documents()[0].file_hash != document.file_hash
    assert manager.pdf_path("handbook.pdf").read_bytes() == updated
    assert "30 days" in manager.ask("How long?").sources[0].text

    manager.delete_document("handbook.pdf")
    assert manager.documents() == []
    assert not manager.pdf_path("handbook.pdf").exists()
