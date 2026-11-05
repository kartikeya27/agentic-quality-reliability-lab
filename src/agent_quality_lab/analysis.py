"""Flakiness analysis and transparent risk/tag coverage optimization."""
from collections import defaultdict
from .schemas import GoldCase


def analyze_flaky(rows: list[dict], min_runs: int = 3) -> dict:
    observations: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        observations[str(row["test_id"])].append(bool(row["passed"]))
    findings = []
    for test_id, runs in sorted(observations.items()):
        pass_rate = sum(runs)/len(runs)
        if len(runs) < min_runs:
            status = "insufficient_data"
        elif pass_rate == 1:
            status = "stable_pass"
        elif pass_rate == 0:
            status = "stable_fail"
        else:
            status = "flaky"
        findings.append({"test_id": test_id, "runs": len(runs), "pass_rate": round(pass_rate, 3), "status": status})
    return {"findings": findings, "flaky_count": sum(r["status"] == "flaky" for r in findings)}

RISK_WEIGHTS = {"critical": 5, "security": 5, "reliability": 4, "negative": 3, "cloud": 2, "observability": 2}


def select_cases(cases: list[GoldCase], budget: int) -> dict:
    """Select the highest marginal risk-weighted *tag* coverage with a case-count budget.
    This is not code coverage or a claim of statistically optimal selection.
    """
    if budget < 1:
        raise ValueError("Budget must be at least 1")
    universe = {tag for case in cases for tag in case.tags}
    selected: list[GoldCase] = []
    remaining = list(cases)
    covered: set[str] = set()
    while remaining and len(selected) < budget:
        ranked = sorted(remaining, key=lambda c: (
            -sum(RISK_WEIGHTS.get(tag, 1) for tag in set(c.tags) - covered), c.id
        ))
        winner = ranked[0]
        selected.append(winner)
        covered.update(winner.tags)
        remaining.remove(winner)
    return {"budget": budget, "selected_ids": [c.id for c in selected],
            "covered_tags": sorted(covered), "uncovered_tags": sorted(universe - covered),
            "tag_coverage_ratio": round(len(covered)/len(universe), 4) if universe else 0.0,
            "method": "greedy risk-weighted tag set cover (not code coverage)"}
