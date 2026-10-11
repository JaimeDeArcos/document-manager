"""Small, explicit configuration surface for the local example."""

from dataclasses import dataclass
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    ollama_host: str
    embedding_model: str
    chat_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("DOCUMENT_MANAGER_DATA_DIR", PROJECT_ROOT / "data")).expanduser(),
            ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            embedding_model=os.getenv("DOCUMENT_MANAGER_EMBED_MODEL", "embeddinggemma"),
            chat_model=os.getenv("DOCUMENT_MANAGER_CHAT_MODEL", "gemma3:4b"),
        )

    @property
    def pdf_dir(self) -> Path:
        return self.data_dir / "pdfs"

    @property
    def vector_dir(self) -> Path:
        return self.data_dir / "chroma"
