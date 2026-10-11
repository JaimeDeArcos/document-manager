from document_manager.models import Chunk
from document_manager.store import VectorStore
import pytest


def test_replacing_a_pdf_removes_old_chunks(tmp_path):
    store = VectorStore(tmp_path / "vectors")
    old = Chunk("old", "old policy", "policy.pdf", 1, "Old", "hash1")
    new = Chunk("new", "new policy", "policy.pdf", 2, "New", "hash2")

    store.replace("policy.pdf", [old], [[1.0, 0.0]])
    assert store.has_version("policy.pdf", "hash1")
    store.replace("policy.pdf", [new], [[0.0, 1.0]])

    assert not store.has_version("policy.pdf", "hash1")
    assert store.documents()[0].chunks == 1
    result = store.search([0.0, 1.0])
    assert [(source.id, source.page, source.section) for source in result] == [
        ("new", 2, "New")
    ]

    store.delete("policy.pdf")
    assert store.documents() == []


def test_failed_second_batch_leaves_previous_document(tmp_path, monkeypatch):
    store = VectorStore(tmp_path / "vectors")
    old = Chunk("old", "current policy", "policy.pdf", 1, "Current", "hash1")
    store.replace("policy.pdf", [old], [[1.0, 0.0]])
    chunks = [Chunk(f"new-{i}", f"text {i}", "policy.pdf", 1, "New", "hash2") for i in range(33)]
    original_upsert = store.collection.upsert
    calls = 0

    def fail_second_batch(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("batch failed")
        return original_upsert(**kwargs)

    monkeypatch.setattr(store.collection, "upsert", fail_second_batch)
    with pytest.raises(RuntimeError, match="batch failed"):
        store.replace("policy.pdf", chunks, [[0.0, 1.0]] * len(chunks))

    assert store.collection.get()["ids"] == ["old"]
    assert store.has_version("policy.pdf", "hash1")
