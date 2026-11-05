import pytest
from agent_quality_lab.model_experiment import compare_live_model
from agent_quality_lab.agent import AgentRunner
from agent_quality_lab.llm import ModelClient
from agent_quality_lab.evaluation import load_golden
from agent_quality_lab.gpu_benchmark import run_gpu_inference_probe

class FakeModel(ModelClient):
    def __init__(self):
        super().__init__(mode='nim')
    def complete_json(self, prompt):
        from agent_quality_lab.agent import baseline_decision
        message = prompt.rsplit('INCIDENT TEXT:\n', 1)[-1]
        return baseline_decision(message).model_dump()


def test_real_model_experiment_seam_injected_model():
    cases = load_golden('data/golden_cases.jsonl')[:3]
    report = compare_live_model(cases, AgentRunner(FakeModel()))
    assert report['model_execution_verified']
    assert report['candidate']['model_used_rate'] == 1
    assert report['delta']['pass_rate'] == 0


def test_model_experiment_requires_real_mode():
    with pytest.raises(ValueError):
        compare_live_model(load_golden('data/golden_cases.jsonl')[:1], AgentRunner(ModelClient(mode='deterministic')))


def test_gpu_probe_without_gpu_cannot_claim_coverage(monkeypatch):
    monkeypatch.setattr('agent_quality_lab.gpu_benchmark.gpu_diagnostic', lambda: {'available': False})
    with pytest.raises(RuntimeError, match='accelerator GPU not detected'):
        run_gpu_inference_probe(AgentRunner(FakeModel()))
