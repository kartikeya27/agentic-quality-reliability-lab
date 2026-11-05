"""Unit/contract checks for new verification machinery; no infrastructure implied."""
import json
from pathlib import Path
from unittest.mock import MagicMock

from agent_quality_lab.readiness import check_readiness
from agent_quality_lab.mutation_benchmark import benchmark_mutations
from agent_quality_lab.evaluation import load_golden


def test_missing_runtime_is_explicit(monkeypatch):
    monkeypatch.setattr('agent_quality_lab.readiness.shutil.which', lambda _name: None)
    monkeypatch.setattr('agent_quality_lab.readiness.gpu_diagnostic', lambda: {'available': False})
    monkeypatch.setenv('AQ_MODE', 'deterministic')
    report = check_readiness()
    assert not report['docker_daemon']['available']
    assert not report['ollama_runtime']['available']
    assert report['gpu']['available'] is False
    assert report['model']['actual_inference_verified'] is False


def test_readiness_real_probe_only_with_opt_in(monkeypatch):
    calls = []
    class Stub:
        def complete_json(self, text):
            calls.append(text)
            return {'category':'network','severity':'high'}
    monkeypatch.setenv('AQ_MODE','nim')
    monkeypatch.setattr('agent_quality_lab.readiness.ModelClient', Stub)
    monkeypatch.setattr('agent_quality_lab.readiness.gpu_diagnostic', lambda: {'available': False})
    assert check_readiness(probe_model=False)['model']['actual_inference_verified'] is False
    assert calls == []
    assert check_readiness(probe_model=True)['model']['actual_inference_verified'] is True
    assert len(calls) == 1


def test_mutation_benchmark_detects_controlled_faults():
    cases = load_golden(Path(__file__).resolve().parents[1] / 'data/golden_cases.jsonl')
    report = benchmark_mutations(cases, 6)
    assert report['total_mutations'] == 6
    assert report['full_detected'] == 6
    assert 0 <= report['selected_mutation_detection_ratio'] <= 1
    assert report['selected_case_count'] == 6


def test_prometheus_grafana_stack_http_check_with_mock(monkeypatch):
    import importlib.util
    p = Path(__file__).resolve().parents[1] / 'scripts/verify_stack_http.py'
    spec = importlib.util.spec_from_file_location('verify_stack_http', p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    class Response:
        status_code = 200
        def __init__(self, data=None, text=''):
            self._data = data
            self.text = text
        def json(self): return self._data
        def raise_for_status(self): return None
    def fake_get(url, **kwargs):
        if url.endswith('/api/health'): return Response({'status':'ok'})
        if url.endswith('/metrics'): return Response(text='aq_triage_requests_total\naq_qa_pass_ratio')
        if url.endswith('/api/v1/query'): return Response({'data':{'result':[{'value':[123, '1']} ]}})
        if url.endswith('/api/search'): return Response([{'uid':'agent-quality-lab'}])
        if url.endswith('/api/dashboards/uid/agent-quality-lab'):
            return Response({'dashboard': {'uid':'agent-quality-lab', 'panels': [{} for _ in range(5)]}})
        if url.endswith('/api/datasources'): return Response([{'type':'prometheus'}])
        return Response({'status':'ok'})
    monkeypatch.setattr(module, '_await_http', lambda url, **kwargs: fake_get(url))
    monkeypatch.setattr(module.httpx, 'get', fake_get)
    monkeypatch.setattr(module.httpx, 'post', lambda *args, **kwargs: Response({'runbook_id':'RB-DATABASE-02'}))
    report = module.check_stack()
    assert report['verified'] is True
    assert all(report['checks'].values())
