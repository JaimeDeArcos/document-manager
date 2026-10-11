import json
from types import SimpleNamespace

import pytest

from document_manager.config import Settings
from document_manager.llm import ANSWER_SCHEMA, LocalModels, NOT_FOUND
from document_manager.models import Source


class FakeClient:
    def __init__(self, payload):
        self.payload = payload
        self.last_request = None

    def chat(self, **kwargs):
        self.last_request = kwargs
        return SimpleNamespace(message=SimpleNamespace(content=json.dumps(self.payload)))


@pytest.fixture
def models(tmp_path):
    settings = Settings(tmp_path, "http://127.0.0.1:11434", "embed", "chat")
    return LocalModels(settings)


def test_citation_must_refer_to_a_retrieved_source(models):
    source = Source("id", "Notes are kept for 90 days", "handbook.pdf", 1, "Retention")
    models.client = FakeClient({"found": True, "answer": "90 days", "citations": [2]})

    answer = models.answer("How long?", [source])

    assert not answer.found
    assert answer.text == NOT_FOUND


def test_valid_citation_is_returned_with_its_metadata(models):
    source = Source("id", "Notes are kept for 90 days", "handbook.pdf", 1, "Retention")
    models.client = FakeClient({"found": True, "answer": "90 days", "citations": [1]})

    answer = models.answer("How long?", [source])

    assert answer.found
    assert answer.sources == (source,)
    assert models.client.last_request["format"] == ANSWER_SCHEMA


def test_non_object_json_is_rejected(models):
    source = Source("id", "text", "handbook.pdf", 1, "Retention")
    models.client = FakeClient([])
    with pytest.raises(ValueError, match="readable answer"):
        models.answer("Question", [source])
