"""Persistent local vector storage with explicit, caller-provided embeddings."""

from collections import Counter
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from .models import Chunk, Document, Source


class VectorStore:
    def __init__(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(
            path=str(directory),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = client.get_or_create_collection(name="pdf_chunks")

    def documents(self) -> list[Document]:
        records = self.collection.get(include=["metadatas"])
        counts: Counter[tuple[str, str]] = Counter()
        for metadata in records["metadatas"] or []:
            counts[(str(metadata["filename"]), str(metadata["file_hash"]))] += 1
        return sorted(
            (Document(name, digest, count) for (name, digest), count in counts.items()),
            key=lambda item: item.filename.lower(),
        )

    def has_version(self, filename: str, file_hash: str) -> bool:
        return any(
            doc.filename == filename and doc.file_hash == file_hash
            for doc in self.documents()
        )

    def replace(self, filename: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("Every chunk needs one embedding.")
        old_ids = set(self.collection.get(where={"filename": filename})["ids"])
        new_ids = {chunk.id for chunk in chunks}

        # Add new vectors first, so a failed upload does not erase the old index.
        try:
            for start in range(0, len(chunks), 32):
                batch = chunks[start : start + 32]
                self.collection.upsert(
                    ids=[chunk.id for chunk in batch],
                    documents=[chunk.text for chunk in batch],
                    embeddings=vectors[start : start + 32],
                    metadatas=[
                        {
                            "filename": chunk.filename,
                            "page": chunk.page,
                            "section": chunk.section,
                            "file_hash": chunk.file_hash,
                        }
                        for chunk in batch
                    ],
                )
        except Exception:
            # A later batch can fail after earlier new chunks were inserted.
            # Remove only the new IDs and preserve the previous document.
            inserted = list(set(self.collection.get(ids=list(new_ids))["ids"]) - old_ids)
            if inserted:
                self.collection.delete(ids=inserted)
            raise
        stale_ids = list(old_ids - new_ids)
        if stale_ids:
            self.collection.delete(ids=stale_ids)

    def search(self, vector: list[float], limit: int = 5) -> list[Source]:
        if self.collection.count() == 0:
            return []
        results = self.collection.query(
            query_embeddings=[vector],
            n_results=min(limit, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        sources = []
        for id_, text, metadata, distance in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            sources.append(
                Source(
                    id=id_,
                    text=text,
                    filename=str(metadata["filename"]),
                    page=int(metadata["page"]),
                    section=str(metadata["section"]),
                    distance=float(distance),
                )
            )
        return sources

    def delete(self, filename: str) -> None:
        ids = self.collection.get(where={"filename": filename})["ids"]
        if ids:
            self.collection.delete(ids=ids)
