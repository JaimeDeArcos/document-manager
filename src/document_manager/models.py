"""Types shared by extraction, indexing, retrieval, and the UI."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    filename: str
    page: int
    section: str
    file_hash: str


@dataclass(frozen=True)
class Document:
    filename: str
    file_hash: str
    chunks: int


@dataclass(frozen=True)
class Source:
    id: str
    text: str
    filename: str
    page: int
    section: str
    distance: float | None = None


@dataclass(frozen=True)
class Answer:
    text: str
    sources: tuple[Source, ...]
    found: bool
