import json
from pathlib import Path
import pytest
from agent_quality_lab.slo import evaluate_slo
from agent_quality_lab.reproduction import load_issues, reproduce, verify_fix
from agent_quality_lab.requirements import trace_requirements


def test_slo_gate_accepts_realistic_report():
    report = {"requests": 30, "successful": 30, "failed": 0, "p95_ms": 125.0,
              "p99_ms": 150.0, "throughput_rps": 22.2}
    result = evaluate_slo(report)
    assert result["passed"] and all(result["checks"].values())


def test_slo_gate_rejects_slow_or_invalid_report():
    bad = {"requests": 30, "successful": 27, "failed": 3, "p95_ms": 9000,
           "p99_ms": 11000, "throughput_rps": 1}
    result = evaluate_slo(bad)
    assert not result["passed"]
    assert not result["checks"]["http_error_rate"]
    assert not result["checks"]["p95_latency"]
    with pytest.raises(ValueError, match="Inconsistent"):
        evaluate_slo(dict(bad, successful=31))
    with pytest.raises(ValueError):
        evaluate_slo(bad, max_error_rate=2)


def test_synthetic_customer_bug_red_green():
    issue = load_issues("data/customer_issues.jsonl")["SYN-DB-001"]
    before = reproduce(issue, inject_fault=True)
    after = reproduce(issue, inject_fault=False)
    assert before["synthetic_fixture"] and not before["passed"]
    assert after["passed"]
    assert verify_fix(before, after)["passed"]
    assert before["tool_trace"][0]["tool"] == "lookup_runbook"


def test_synthetic_customer_bug_oracle_is_immutable():
    issue = load_issues("data/customer_issues.jsonl")["SYN-DB-001"]
    before, after = reproduce(issue, inject_fault=True), reproduce(issue, inject_fault=False)
    changed = dict(after, expected={"category": "general"})
    with pytest.raises(ValueError, match="changed oracle"):
        verify_fix(before, changed)
    changed = dict(after, issue_id="SYN-OTHER")
    with pytest.raises(ValueError, match="same synthetic issue"):
        verify_fix(before, changed)


def test_traceability_rejects_nonexistent_test():
    root = Path(".")
    req = [{"id": "A", "requirement": "example", "test_refs": ["tests/test_agent.py::not_a_real_test"]}]
    with pytest.raises(ValueError, match="Missing executed test"):
        trace_requirements(req, {}, root)
    with pytest.raises(ValueError, match="unique"):
        trace_requirements(req * 2, {}, root)


def test_kubernetes_and_ci_artifacts_are_present():
    for path in ("Dockerfile", "docker-compose.yml", "k8s/deployment.yaml",
                 ".github/workflows/quality.yml", "scripts/verify_k8s_kind.sh",
                 "scripts/kwok_failure_experiment.sh"):
        assert Path(path).is_file()
    # These are config-existence assertions, NOT actual cluster execution.
    assert "verify_k8s_kind" in Path(".github/workflows/quality.yml").read_text()


def test_nemo_policy_scoped_heuristic_and_review_flag():
    from agent_quality_lab.nemo_policy_eval import load_policy_cases, run_policy_eval
    cases = load_policy_cases("data/guardrail_cases.jsonl")
    class FakeRails:
        def generate(self, messages):
            message = messages[0]["content"]
            block = any(x in message for x in ("Ignore", "Pretend"))
            return {"content": "I'm sorry, I can't help with that." if block else "Review metrics and inspect read-only logs."}
    result = run_policy_eval("unused", cases, rails_factory=lambda _: FakeRails())
    assert result["heuristic_score"] == 1.0
    assert result["policy_effectiveness_verified"] is False
    assert all(item["requires_human_review"] for item in result["cases"])


def test_nemo_policy_heuristic_does_not_fake_security_efficacy():
    from agent_quality_lab.nemo_policy_eval import run_policy_eval
    class WeakRails:
        def generate(self, messages):
            return {"content": "Sure, do it"}
    result = run_policy_eval("unused", [{"id":"deny", "prompt":"untrusted", "expected":"block"}],
                             rails_factory=lambda _: WeakRails())
    assert result["heuristic_score"] == 0
    assert not result["policy_effectiveness_verified"]
