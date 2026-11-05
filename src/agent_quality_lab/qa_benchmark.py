"""Measured local execution cost of full vs risk-selected regression suites.

This deliberately does not label the selector "AI" or claim higher defect detection.
"""
from datetime import datetime, timezone
from time import perf_counter
from .analysis import select_cases
from .evaluation import evaluate


def compare_regression_effort(runner, cases, budget: int) -> dict:
    if budget <= 0 or not cases:
        raise ValueError("budget and cases must be positive")
    start = perf_counter()
    full = evaluate(runner, cases)
    full_seconds = perf_counter() - start
    selection = select_cases(cases, budget)
    subset = [c for c in cases if c.id in selection["selected_ids"]]
    start = perf_counter()
    reduced = evaluate(runner, subset)
    selected_seconds = perf_counter() - start
    n = len(cases)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "mode": runner.model.mode,
        "full": {"cases": n, "seconds": round(full_seconds, 6), "pass_rate": full["summary"]["pass_rate"]},
        "selected": {"cases": len(subset), "seconds": round(selected_seconds, 6), "pass_rate": reduced["summary"]["pass_rate"],
                     "tag_coverage_ratio": selection["tag_coverage_ratio"]},
        "case_reduction_ratio": round(1 - len(subset)/n, 4),
        "observed_time_reduction_ratio": round(1 - selected_seconds/full_seconds, 4) if full_seconds else 0,
        "known_uncovered_failing_cases": sorted({r["id"] for r in full["cases"] if not r["passed"]} - set(selection["selected_ids"])),
        "limitations": "Paired sequential runs on one machine; caching and measurement noise affect timing. Risk-tag coverage is not code coverage. Not a measured AI uplift. Reduced regression scope can miss defects.",
    }
