"""Pure checks for evidence integrity; synthetic inputs are not live evidence."""
import pytest
from scripts.productivity_experiment import analyze
from scripts.verify_gpu_residency import parse_compute_processes


def observations():
    rows=[]
    for n in range(4):
        rows.extend([
            dict(task_id=f'TASK-{n}',method='manual',minutes='12',valid_defects='1',false_positives='0',reviewer='R',order='first' if n%2 else 'second',model_used='false'),
            dict(task_id=f'TASK-{n}',method='ai',minutes='10',valid_defects='1',false_positives='0',reviewer='R',order='second' if n%2 else 'first',model_used='true'),
        ])
    return rows


def test_productivity_calculates_only_from_observations():
    result=analyze(observations())
    assert result['paired_tasks']==4
    assert result['minutes_manual']==48
    assert result['minutes_ai']==40
    assert result['total_time_saved_minutes']==8
    assert result['observed_time_change_percent']<0


def test_productivity_does_not_accept_fallback():
    r=observations()
    r[1]['model_used']='false'
    with pytest.raises(ValueError,match='model_used=true'):
        analyze(r)


def test_productivity_requires_complete_pairs():
    with pytest.raises(ValueError,match='at least 4'):
        analyze(observations()[:-1])


def test_productivity_rejects_fake_duration():
    r=observations()
    r[0]['minutes']='nan'
    with pytest.raises(ValueError,match='duration'):
        analyze(r)


def test_gpu_process_proof_requires_matching_positive_memory():
    data='123, /usr/bin/ollama_llama_server, 536\n234, firefox, 400\n345, /usr/bin/ollama, 0\n'
    assert parse_compute_processes(data,'ollama')==[{'pid':'123','process':'/usr/bin/ollama_llama_server','gpu_memory_mib':536}]
    assert parse_compute_processes(data,'vllm')==[]
