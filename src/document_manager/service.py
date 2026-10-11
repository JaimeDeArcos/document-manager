"""Index and ask: the small application boundary used by Streamlit."""

from pathlib import Path

from .config import Settings
from .llm import LocalModels, NOT_FOUND
from .models import Answer, Document
from .pdf import extract_chunks
from .store import VectorStore


MAX_PDF_BYTES = 25 * 1024 * 1024


def safe_filename(value: str) -> str:
    name = value.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name or name in {".", ".."} or "\x00" in name or not name.lower().endswith(".pdf"):
        raise ValueError("Choose a PDF file with a valid filename.")
    return name


class DocumentManager:
    def __init__(self, settings: Settings, store: VectorStore | None = None, models: LocalModels | None = None):
        self.settings = settings
        self.store = store or VectorStore(settings.vector_dir)
        self.models = models or LocalModels(settings)

    def documents(self) -> list[Document]:
        return self.store.documents()

    def index_pdf(self, filename: str, contents: bytes) -> tuple[Document, bool]:
        filename = safe_filename(filename)
        if len(contents) > MAX_PDF_BYTES:
            raise ValueError("PDFs larger than 25 MB are not supported in this example.")
        file_hash, chunks = extract_chunks(contents, filename)
        if self.store.has_version(filename, file_hash):
            return Document(filename, file_hash, len(chunks)), False

        vectors = self.models.embed([chunk.text for chunk in chunks])
        if len(vectors) != len(chunks):
            raise ValueError("The embedding model returned the wrong number of vectors.")

        self.settings.pdf_dir.mkdir(parents=True, exist_ok=True)
        target = self.settings.pdf_dir / filename
        temporary = target.with_name(f".{filename}.pending")
        temporary.write_bytes(contents)
        try:
            self.store.replace(filename, chunks, vectors)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        return Document(filename, file_hash, len(chunks)), True

    def ask(self, question: str) -> Answer:
        question = question.strip()
        if not question:
            raise ValueError("Enter a question first.")
        if not self.store.documents():
            return Answer(NOT_FOUND, (), False)
        query_vector = self.models.embed([question])[0]
        return self.models.answer(question, self.store.search(query_vector))

    def delete_document(self, filename: str) -> None:
        filename = safe_filename(filename)
        self.store.delete(filename)
        (self.settings.pdf_dir / filename).unlink(missing_ok=True)

    def pdf_path(self, filename: str) -> Path:
        return self.settings.pdf_dir / safe_filename(filename)
