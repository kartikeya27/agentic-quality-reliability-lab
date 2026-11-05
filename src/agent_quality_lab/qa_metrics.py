"""Export bounded, lower-cardinality QA result metrics from generated reports.

Missing report files must NOT be represented as 100% pass or zero failures.
"""
import json
from pathlib import Path
from prometheus_client import Gauge

PASS = Gauge("aq_qa_pass_ratio", "Last uploaded offline QA report pass fraction", ["suite"])
FLAKY = Gauge("aq_qa_flaky_tests", "Flaky tests in last imported report")
REGRESSIONS = Gauge("aq_qa_regressions", "Number of newly failing cases from compared reports")
TAG_COVERAGE = Gauge("aq_qa_selected_tag_coverage_ratio", "Risk-selected tag coverage fraction (not code coverage)")
QA_P95 = Gauge("aq_qa_load_p95_milliseconds", "Client-measured p95 from most recent local load report")
QA_P99 = Gauge("aq_qa_load_p99_milliseconds", "Client-measured p99 from most recent local load report")
MUTATION = Gauge("aq_qa_controlled_mutation_detection_ratio", "Fraction of seeded mutations detected by full golden suite (not AI uplift)")
BENCH_TIME = Gauge("aq_qa_observed_time_reduction_ratio", "Observed local time reduction via risk selection (not AI uplift)")
SLO_GATE = Gauge("aq_qa_local_http_slo_gate", "Most recent local load SLO gate: 1 pass, 0 failure")
REQ_GATE = Gauge("aq_qa_requirement_offline_gate", "Execution-backed offline requirement traceability: 1 pass, 0 fail")
BUG_GATE = Gauge("aq_qa_synthetic_bug_fix_gate", "Synthetic before/after defect reproduction, not production fixes")


def load_metrics(directory: str | Path = "artifacts") -> list[str]:
    directory = Path(directory)
    recognized = []
    inputs = {
        "eval-report.json": lambda d: PASS.labels(suite="golden").set(d["summary"]["pass_rate"]),
        "advanced-report.json": lambda d: PASS.labels(suite="advanced").set(d["summary"]["pass_rate"]),
        "flaky-report.json": lambda d: FLAKY.set(d["flaky_count"]),
        "selected-cases.json": lambda d: TAG_COVERAGE.set(d["tag_coverage_ratio"]),
        "regression-diff.json": lambda d: REGRESSIONS.set(len(d["regressions"])),
        "load-report.json": lambda d: (QA_P95.set(d["p95_ms"]), QA_P99.set(d["p99_ms"])),
        "mutation-report.json": lambda d: MUTATION.set(d["full_mutation_detection_ratio"]),
        "efficiency-report.json": lambda d: BENCH_TIME.set(d["observed_time_reduction_ratio"]),
        "slo-gate-report.json": lambda d: SLO_GATE.set(int(d["passed"])),
        "requirements-traceability.json": lambda d: REQ_GATE.set(int(d["offline_gate_passed"])),
        "defects/fix-verification.json": lambda d: BUG_GATE.set(int(d["passed"])),
    }
    for name, update in inputs.items():
        path = directory / name
        if not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            update(data)
            recognized.append(name)
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            continue
    return recognized
