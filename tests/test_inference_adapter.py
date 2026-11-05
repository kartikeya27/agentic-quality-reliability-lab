"""HTTP adapter contract tests against synthetic responses; do NOT require inference service."""
import json
import httpx
import pytest
from agent_quality_lab.llm import ModelClient, ModelError

class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload

class FakeClient:
    def __init__(self, payload, captured):
        self.payload = payload
        self.captured = captured
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def post(self, url, **kwargs):
        self.captured["url"] = url
        self.captured["payload"] = kwargs["json"]
        self.captured["headers"] = kwargs.get("headers", {})
        return FakeResponse(self.payload)


def test_ollama_chat_protocol(monkeypatch):
    captured = {}
    payload = {"message": {"content": json.dumps({"category": "network", "severity": "high"})}}
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: FakeClient(payload, captured))
    monkeypatch.setenv("AQ_OLLAMA_URL", "http://127.0.0.1:11434")
    result = ModelClient(mode="ollama").complete_json("Synthetic network error")
    assert result["category"] == "network"
    assert captured["url"].endswith("/api/chat")
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["format"] == "json"


def test_openai_compatible_chat_protocol(monkeypatch):
    captured = {}
    payload = {"choices": [{"message": {"content": json.dumps({"category": "identity", "severity": "critical"})}}]}
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: FakeClient(payload, captured))
    monkeypatch.setenv("AQ_OPENAI_BASE_URL", "http://127.0.0.1:8001/v1")
    monkeypatch.setenv("AQ_API_KEY", "synthetic-test-key")
    result = ModelClient(mode="openai_compatible").complete_json("Synthetic identity outage")
    assert result["category"] == "identity"
    assert captured["url"].endswith("/v1/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer synthetic-test-key"


def test_invalid_inference_output_raises_explicit_error(monkeypatch):
    captured = {}
    payload = {"message": {"content": "not json"}}
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: FakeClient(payload, captured))
    with pytest.raises(ModelError, match="inference failed"):
        ModelClient(mode="ollama").complete_json("Synthetic incident")
