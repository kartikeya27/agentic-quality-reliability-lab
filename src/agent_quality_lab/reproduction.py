"""Reproduce synthetic customer bugs and verify failure-to-pass regressions.

No real customer data is saved and no real system mutation occurs.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from .agent import AgentRunner
from .schemas import TriageRequest
from .tools import RUNBOOKS


def load_issues(path: str | Path) -> dict[str, dict]:
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Synthetic reproduction dataset requires unique issue IDs")
    issues = {}
    for row in rows:
        if row.get("expected_category") not in RUNBOOKS or row.get("expected_severity") not in ("medium", "high", "critical"):
            raise ValueError("Invalid expected result")
        if not row.get("id", "").startswith("SYN-") or not row.get("message"):
            raise ValueError("Only annotated synthetic issues are accepted")
        issues[row["id"]] = row
    return issues


class InjectedWrongCategory:
    """A known faulty model used ONLY to demonstrate defect reproduction."""
    mode = "synthetic-fault"
    model = "synthetic-injected-bug"

    def complete_json(self, prompt: str) -> dict:
        return {"category": "general", "severity": "medium"}


def reproduce(issue: dict, *, inject_fault: bool = False) -> dict:
    # No network dependency: explicit offline mode unless intentionally injecting a fake model.
    runner = AgentRunner(InjectedWrongCategory() if inject_fault else None)
    if not inject_fault:
        from .llm import ModelClient
        runner = AgentRunner(ModelClient(mode="deterministic"))
    request = TriageRequest(incident_id=issue["id"], message=issue["message"])
    actual = runner.triage(request)
    expected = {"category": issue["expected_category"], "severity": issue["expected_severity"],
                "runbook_id": RUNBOOKS[issue["expected_category"]]["id"]}
    observed = {"category": actual.category, "severity": actual.severity, "runbook_id": actual.runbook_id}
    checks = {k: observed[k] == expected[k] for k in expected}
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "issue_id": issue["id"],
            "synthetic_fixture": True, "scenario": issue["message"], "repro_mode": "injected_model_bug" if inject_fault else "deterministic_baseline",
            "expected": expected, "observed": observed, "checks": checks, "passed": all(checks.values()),
            "model_used": actual.model_used, "fallback_used": actual.fallback_used,
            "tool_trace": [entry.model_dump() for entry in actual.trace],
            "reproduce_command": f"python -m agent_quality_lab reproduce --issue {issue['id']}" + (" --inject-known-bug" if inject_fault else ""),
            "scope": "Synthetic reproduction evidence; does not establish an actual customer ticket or production incident."}


def markdown_defect(report: dict) -> str:
    return (f"# Synthetic defect reproduction: {report['issue_id']}\n\n"
            f"**Fixture only — no real customer data.**\n\n"
            f"- Command: `{report['reproduce_command']}`\n"
            f"- Mode: `{report['repro_mode']}`\n"
            f"- Expected: `{json.dumps(report['expected'], sort_keys=True)}`\n"
            f"- Actual: `{json.dumps(report['observed'], sort_keys=True)}`\n"
            f"- Reproduced mismatch: **{'no' if report['passed'] else 'yes'}**\n"
            f"- Tool trace: `{json.dumps(report['tool_trace'])}`\n\n"
            "Add a failing regression test, correct the issue, rerun the same fixture, and attach the passing report.\n")


def verify_fix(before: dict, after: dict) -> dict:
    if before.get("issue_id") != after.get("issue_id") or not before.get("synthetic_fixture") or not after.get("synthetic_fixture"):
        raise ValueError("Both reports must cover the same synthetic issue")
    if before.get("expected") != after.get("expected"):
        raise ValueError("Cannot compare a changed oracle")
    checks = {"failing_issue_reproduced": before.get("passed") is False,
              "same_fixture_passing": after.get("passed") is True,
              "expected_unchanged": before["expected"] == after["expected"]}
    return {"issue_id": before["issue_id"], "passed": all(checks.values()), "checks": checks,
            "note": "Demonstrates synthetic red-to-green verification, not a real customer fix or production rollout."}
