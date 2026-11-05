"""Fault injection for model adapters, without contacting external model hosts."""
from .agent import AgentRunner
from .llm import ModelClient, ModelError
from .schemas import TriageRequest


class FaultModel(ModelClient):
    def __init__(self, behavior):
        super().__init__(mode="nim")
        self.behavior = behavior

    def complete_json(self, prompt):
        if self.behavior == "timeout":
            raise ModelError("synthetic model timeout")
        if self.behavior == "http_503":
            raise ModelError("synthetic upstream unavailable")
        if self.behavior == "invalid_schema":
            return {"category": "unapproved_category", "severity": "high"}
        if self.behavior == "good":
            return {"category": "database", "severity": "high"}
        raise ValueError("unknown fault behavior")


def run_inference_faults():
    scenarios = []
    for behavior in ("timeout", "http_503", "invalid_schema", "good"):
        r = AgentRunner(FaultModel(behavior)).triage(
            TriageRequest(incident_id="INFER-FAULT", message="Database query failed"))
        expected_fallback = behavior != "good"
        checks = {
            "explicit_fallback": r.fallback_used == expected_fallback,
            "model_used_only_if_successful": r.model_used == (behavior == "good"),
            "category_preserved": r.category == "database",
            "read_only_tool": r.runbook_id == "RB-DATABASE-02" and r.trace[0].tool == "lookup_runbook",
        }
        scenarios.append({"fault": behavior, "checks": checks, "passed": all(checks.values())})
    return {"passed": all(x["passed"] for x in scenarios), "scenarios": scenarios,
            "scope": "In-process injected inference failures (not real accelerator NIM outage or load test)"}
