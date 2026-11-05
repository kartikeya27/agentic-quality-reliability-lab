import json
from pathlib import Path
from agent_quality_lab.advanced_eval import load_advanced_cases, run_advanced
from agent_quality_lab.agent import AgentRunner
from agent_quality_lab.gpu import gpu_diagnostic
from agent_quality_lab.inference_chaos import run_inference_faults
from agent_quality_lab.kwok_report import inspect_kwok_snapshots
from agent_quality_lab.qa_benchmark import compare_regression_effort
from agent_quality_lab.evaluation import load_golden
from agent_quality_lab.qa_metrics import load_metrics


def test_advanced_offline_checks():
    report = run_advanced(AgentRunner(), load_advanced_cases('data/advanced_cases.jsonl'), repeats=3)
    assert report['summary']['pass_rate'] == 1.0
    assert report['summary']['model_used_rate'] == 0.0
    assert report['summary']['grounded_tool_rate'] == 1.0


def test_inference_chaos_offline():
    assert run_inference_faults()['passed']


def test_efficiency_is_measured_and_qualified():
    report = compare_regression_effort(AgentRunner(), load_golden('data/golden_cases.jsonl'), 6)
    assert report['full']['cases'] == 16
    assert report['selected']['cases'] == 6
    assert report['case_reduction_ratio'] == 0.625
    assert 'not code coverage' in report['limitations']


def test_kwok_snapshot_node_loss():
    def nodes(names): return {'items': [{'metadata': {'name': n}} for n in names]}
    def pods(nodes_): return {'items': [{'spec': {'nodeName': n}} for n in nodes_]}
    report = inspect_kwok_snapshots(nodes(['n1','n2']), nodes(['n2']), pods(['n1','n2']), pods(['n2','n2']), 'n1', 2)
    assert report['passed'] and report['simulation_only']
    assert not inspect_kwok_snapshots(nodes(['n1','n2']), nodes(['n1','n2']), pods(['n1']), pods(['n1']), 'n1', 2)['passed']


def test_gpu_probe_is_nonfatal():
    report = gpu_diagnostic()
    assert isinstance(report['available'], bool)
    assert report['backend'] == 'gpu-monitor-cli'


def test_qa_metrics_from_reports(tmp_path):
    (tmp_path/'advanced-report.json').write_text(json.dumps({'summary': {'pass_rate': 0.75}}))
    (tmp_path/'flaky-report.json').write_text(json.dumps({'flaky_count': 2}))
    assert set(load_metrics(tmp_path)) == {'advanced-report.json','flaky-report.json'}
