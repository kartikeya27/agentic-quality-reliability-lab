"""Isolated network-free contracts and SDK seam checks."""
import httpx
import json
import pytest
from agent_quality_lab.llm import ModelClient, ModelError
from agent_quality_lab.nemo_adapter import run_nemo_smoke
from agent_quality_lab.agent import AgentRunner
from agent_quality_lab.schemas import TriageRequest


def test_nim_uses_configured_openai_protocol(monkeypatch):
    requests = []
    def handler(req: httpx.Request) -> httpx.Response:
        requests.append(req)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"category":"database","severity":"high"}'}}]})
    mock = httpx.MockTransport(handler)
    real = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: real(transport=mock, **kw))
    monkeypatch.setenv("AQ_NIM_BASE_URL", "http://localhost:8001/v1")
    monkeypatch.setenv("AQ_NIM_API_KEY", "test-only")
    monkeypatch.setenv("AQ_NIM_MODEL", "synthetic/nim")
    output = ModelClient(mode="nim").complete_json("Database query failed")
    assert output["category"] == "database"
    req = requests[0]
    assert str(req.url) == "http://localhost:8001/v1/chat/completions"
    assert req.headers["Authorization"] == "Bearer test-only"
    assert json.loads(req.content)["model"] == "synthetic/nim"


@pytest.mark.parametrize("fault", ["server_error", "timeout", "invalid_json", "invalid_decision"])
def test_nim_faults_are_visible_as_fallback(monkeypatch, fault):
    def handler(request):
        if fault == "timeout":
            raise httpx.ReadTimeout("simulated", request=request)
        if fault == "server_error":
            return httpx.Response(503, json={"error": "simulated"})
        content = "not-json" if fault == "invalid_json" else '{"category":"invented","severity":"high"}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})
    real = httpx.Client
    mock = httpx.MockTransport(handler)
    monkeypatch.setattr(httpx, "Client", lambda **kw: real(transport=mock, **kw))
    response = AgentRunner(ModelClient(mode="nim")).triage(TriageRequest(incident_id="NIM-FAULT", message="Database query failed"))
    assert response.category == "database"
    assert response.model_used is False
    assert response.fallback_used is True
    assert response.runbook_id == "RB-DATABASE-02"


def test_nemo_sdk_dispatch_with_fake_factory():
    class Stub:
        def generate(self, messages):
            assert messages[0]["role"] == "user"
            return {"role": "assistant", "content": "This is a mocked NeMo SDK contract."}
    response = run_nemo_smoke(rails_factory=lambda cfg: Stub())
    assert response["sdk_executed"] is True
    assert "mocked" in response["content"]


def test_nemo_configuration_declares_rails():
    from pathlib import Path
    config = Path("nemo/guardrails/config.yml").read_text()
    prompts = Path("nemo/guardrails/prompts.yml").read_text()
    for name in ("self check input", "self check output"):
        assert name in config
    for name in ("self_check_input", "self_check_output"):
        assert name in prompts
