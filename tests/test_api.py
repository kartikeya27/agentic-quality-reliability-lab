from fastapi.testclient import TestClient
from agent_quality_lab.api import create_app
from agent_quality_lab.agent import AgentRunner
from agent_quality_lab.llm import ModelClient

client = TestClient(create_app(AgentRunner(ModelClient(mode="deterministic"))))


def test_health_is_not_inference_check():
    r = client.get("/api/health")
    assert r.status_code == 200 and "not an inference" in r.json()["note"]


def test_valid_triage_and_tool_trace():
    r = client.post("/api/triage", json={"incident_id": "API-1", "message": "Deployment failed"})
    assert r.status_code == 200
    assert r.json()["trace"][0]["status"] == "ok"


def test_fault_endpoint_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AQ_ENABLE_FAULTS", raising=False)
    r = client.post("/api/triage", json={"incident_id": "API-2", "message": "Database failed", "fault": "timeout"})
    assert r.status_code == 403


def test_fault_endpoint_enabled_only_in_demo(monkeypatch):
    monkeypatch.setenv("AQ_ENABLE_FAULTS", "1")
    r = client.post("/api/triage", json={"incident_id": "API-3", "message": "Database failed", "fault": "timeout"})
    assert r.status_code == 200 and r.json()["degraded"]


def test_input_contract_rejects_extra_fields():
    r = client.post("/api/triage", json={"incident_id": "ABC", "message": "hi", "dangerous": "extra"})
    assert r.status_code == 422


def test_metrics_exposed_without_message_labels():
    r = client.get("/metrics")
    assert r.status_code == 200 and "aq_triage_requests_total" in r.text
    assert "incident_id=" not in r.text
