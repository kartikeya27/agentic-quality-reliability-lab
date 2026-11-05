from pathlib import Path
import json
from agent_quality_lab.agent import AgentRunner
from agent_quality_lab.llm import ModelClient
from agent_quality_lab.evaluation import load_golden, evaluate, compare_reports, write_report, percentile
from agent_quality_lab.analysis import analyze_flaky, select_cases
from agent_quality_lab.testgen import generate_metamorphic

ROOT = Path(__file__).resolve().parents[1]
CASES = load_golden(ROOT / "data/golden_cases.jsonl")


def test_golden_quality_gate(tmp_path):
    report = evaluate(AgentRunner(ModelClient(mode="deterministic")), CASES)
    assert report["summary"]["pass_rate"] == 1
    assert report["summary"]["model_used_rate"] == 0
    output = tmp_path / "report.json"
    write_report(report, output)
    assert output.exists() and output.with_suffix(".md").exists()


def test_flaky_vs_stable_failure():
    rows = [json.loads(line) for line in (ROOT / "data/flaky_runs.jsonl").read_text().splitlines()]
    result = analyze_flaky(rows)
    statuses = {x["test_id"]: x["status"] for x in result["findings"]}
    assert statuses == {"test_login": "flaky", "test_database": "stable_pass", "test_deploy": "stable_fail", "test_network": "insufficient_data"}


def test_coverage_selector_and_budget():
    out = select_cases(CASES, budget=5)
    assert len(out["selected_ids"]) == 5
    assert 0 < out["tag_coverage_ratio"] <= 1
    assert not set(out["covered_tags"]) & set(out["uncovered_tags"])


def test_generated_metamorphic_cases():
    generated = generate_metamorphic(CASES, limit=7)
    assert len(generated) == 7
    assert all("metamorphic" in c["tags"] for c in generated)
    assert generated[0]["message"].isupper()


def test_comparison_detects_new_regression():
    baseline = {"cases": [{"id": "a", "passed": True}, {"id": "b", "passed": False}]}
    current = {"cases": [{"id": "a", "passed": False}, {"id": "b", "passed": True}]}
    result = compare_reports(baseline, current)
    assert result["regressions"] == ["a"] and result["fixed"] == ["b"]


def test_percentile_nearest_rank():
    assert percentile([1, 2, 3, 4], 0.95) == 4
