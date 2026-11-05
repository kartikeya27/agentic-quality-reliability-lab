"""Golden-dataset evaluation, machine-readable evidence, and regression comparison."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .agent import AgentRunner
from .schemas import GoldCase, TriageRequest


def read_jsonl(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def load_golden(path: str | Path) -> list[GoldCase]:
    cases = [GoldCase.model_validate(case) for case in read_jsonl(path)]
    ids = [case.id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate golden case IDs")
    if not cases:
        raise ValueError("Golden dataset is empty")
    return cases


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    import math
    return ordered[max(0, math.ceil(p * len(ordered)) - 1)]


def evaluate(runner: AgentRunner, cases: list[GoldCase]) -> dict:
    rows = []
    for case in cases:
        got = runner.triage(TriageRequest(incident_id=case.id, message=case.message))
        checks = {
            "category": got.category == case.expected_category,
            "severity": got.severity == case.expected_severity,
            "tool": len(got.trace) == 1 and got.trace[0].status == "ok",
            "output_contract": bool(got.steps and got.team and got.runbook_id),
            "safe": not got.degraded,
        }
        rows.append({
            "id": case.id, "passed": all(checks.values()), "checks": checks,
            "expected": {"category": case.expected_category, "severity": case.expected_severity},
            "actual": {"category": got.category, "severity": got.severity, "runbook_id": got.runbook_id},
            "model_used": got.model_used, "fallback_used": got.fallback_used,
            "latency_ms": got.latency_ms, "tags": case.tags,
        })
    n = len(rows)
    failures = [r for r in rows if not r["passed"]]
    used = sum(r["model_used"] for r in rows)
    fallback = sum(r["fallback_used"] for r in rows)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "mode": runner.model.mode,
        "model": runner.model.model if runner.model.mode != "deterministic" else None,
        "summary": {
            "total": n, "passed": n-len(failures), "failed": len(failures),
            "pass_rate": round((n-len(failures))/n, 4),
            "category_accuracy": round(sum(r["checks"]["category"] for r in rows)/n, 4),
            "severity_accuracy": round(sum(r["checks"]["severity"] for r in rows)/n, 4),
            "model_used_rate": round(used/n, 4), "fallback_rate": round(fallback/n, 4),
            "p50_ms": round(percentile([r["latency_ms"] for r in rows], .50), 2),
            "p95_ms": round(percentile([r["latency_ms"] for r in rows], .95), 2),
        }, "cases": rows,
    }


def write_report(report: dict, output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    s = report["summary"]
    md = f"# Agent quality evaluation\n\nMode: `{report['mode']}` · Model: `{report.get('model') or 'none'}`\n\n"
    md += f"| Metric | Value |\n| --- | ---: |\n| Cases | {s['total']} |\n| Passed | {s['passed']} |\n| Pass rate | {s['pass_rate']:.1%} |\n| Category accuracy | {s['category_accuracy']:.1%} |\n| Severity accuracy | {s['severity_accuracy']:.1%} |\n| Model actually used | {s['model_used_rate']:.1%} |\n| Inference fallback | {s['fallback_rate']:.1%} |\n| p95 latency | {s['p95_ms']:.2f} ms |\n\n"
    md += "## Failing cases\n\n"
    failures = [r for r in report["cases"] if not r["passed"]]
    md += "\n".join(f"- `{r['id']}`: {', '.join(k for k,v in r['checks'].items() if not v)}; expected {r['expected']}; actual {r['actual']}" for r in failures) if failures else "No failures."
    path.with_suffix(".md").write_text(md + "\n", encoding="utf-8")
    return path


def compare_reports(before: dict, after: dict) -> dict:
    b = {r["id"]: r for r in before["cases"]}
    a = {r["id"]: r for r in after["cases"]}
    common = sorted(b.keys() & a.keys())
    if not common:
        raise ValueError("No common case IDs for regression comparison")
    return {
        "comparable_cases": len(common),
        "regressions": [id for id in common if b[id]["passed"] and not a[id]["passed"]],
        "fixed": [id for id in common if not b[id]["passed"] and a[id]["passed"]],
        "unchanged_failures": [id for id in common if not b[id]["passed"] and not a[id]["passed"]],
        "only_before": sorted(b.keys() - a.keys()),
        "only_after": sorted(a.keys() - b.keys()),
    }
