"""New v0.4 checks: no fake pass when real infrastructure is missing."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_loopback_http_adapters_without_real_services():
    mod = load_script('verify_backend_http_contract')
    report = mod.run()
    assert report['verified'] is True
    assert report['calls'][0]['path'] == '/api/chat'
    assert report['calls'][1]['path'] == '/v1/chat/completions'
    assert 'synthetic' in report['scope']


def test_integrations_audit_cannot_mark_missing_runtime_as_verified(monkeypatch):
    mod = load_script('audit_integrations')
    monkeypatch.setattr(mod, 'docker_usable', lambda: False)
    monkeypatch.setattr(mod, 'command_exists', lambda _: False)
    monkeypatch.delenv('AQ_NIM_BASE_URL', raising=False)
    monkeypatch.delenv('AQ_NIM_MODEL', raising=False)
    result = mod.audit(list(mod.PROFILES), execute=False)
    assert result['verified'] == 0
    assert result['failed'] == 0
    assert result['blocked'] == 7
    assert all(row['status'] == 'BLOCKED' for row in result['checks'].values())


def test_audit_nested_evidence_requires_explicit_true():
    mod = load_script('audit_integrations')
    assert mod.nested_truth({'model': {'actual_inference_verified': True}}, 'model.actual_inference_verified')
    assert not mod.nested_truth({'model': {'actual_inference_verified': 1}}, 'model.actual_inference_verified')
    assert not mod.nested_truth({'model': {}}, 'model.actual_inference_verified')
    assert not mod.nested_truth({}, 'model.actual_inference_verified')
