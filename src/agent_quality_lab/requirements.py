"""Job-requirement traceability tied to *executed* Pytest XML evidence.

A source path or YAML file is not proof an integration ran. This report never
confuses code links and passing offline tests with external service execution.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def load_test_outcomes(junit: str | Path) -> dict[str, str]:
    tree = ET.parse(junit)
    outcomes = {}
    for node in tree.iter("testcase"):
        classname = node.get("classname", "")
        path = classname.replace(".", "/") + ".py"
        name = node.get("name", "")
        status = "failed" if node.find("failure") is not None or node.find("error") is not None else (
            "skipped" if node.find("skipped") is not None else "passed")
        outcomes[f"{path}::{name}"] = status
    return outcomes


def trace_requirements(requirements: list[dict], outcomes: dict[str, str], root: str | Path) -> dict:
    root = Path(root)
    ids = [r["id"] for r in requirements]
    if len(set(ids)) != len(ids) or not ids:
        raise ValueError("Requirement identifiers must be unique and nonempty")
    rows = []
    for req in requirements:
        refs = req.get("test_refs", [])
        if not refs:
            raise ValueError("Every trackable requirement must have a specific automated test")
        tests = []
        for ref in refs:
            if "::" not in ref or not (root / ref.split("::", 1)[0]).is_file():
                raise ValueError(f"Invalid test path for {req['id']}: {ref}")
            if ref not in outcomes:
                raise ValueError(f"Missing executed test for {req['id']}: {ref}")
            tests.append({"id": ref, "status": outcomes[ref]})
        test_gate = all(t["status"] == "passed" for t in tests)
        rows.append({"id": req["id"], "requirement": req["requirement"],
                     "test_gate_passed": test_gate, "offline_test_results": tests,
                     "optional_verification": req.get("optional_verification"),
                     "external_runtime_verified_by_this_report": False})
    return {"generated_at": datetime.now(timezone.utc).isoformat(),
            "requirements_tracked": len(rows), "offline_tests_passed": sum(r["test_gate_passed"] for r in rows),
            "offline_gate_passed": all(r["test_gate_passed"] for r in rows),
            "external_integrations_verified": False, "requirements": rows,
            "scope": "Executed unit/contract tests from JUnit XML. Does not prove cloud deployment, model inference, NeMo policy efficacy, GitHub Actions, user experience, or team qualifications."}


def trace_from_files(requirements_path: str, junit_path: str, root: str = ".") -> dict:
    requirements = json.loads(Path(requirements_path).read_text(encoding="utf-8"))
    return trace_requirements(requirements, load_test_outcomes(junit_path), root)
