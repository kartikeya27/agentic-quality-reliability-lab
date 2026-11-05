#!/usr/bin/env python3
"""Verify inference and local accelerator GPU process memory overlap on ONE host.

A hosted accelerator endpoint cannot pass this test merely because local GPU exists.
"""
import argparse
import json
import os
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from agent_quality_lab.agent import AgentRunner
from agent_quality_lab.schemas import TriageRequest


def parse_compute_processes(raw: str, process_hint: str) -> list[dict]:
    result=[]
    for line in raw.splitlines():
        parts=[x.strip() for x in line.split(',')]
        if len(parts)<3:continue
        pid, process, mem=parts[:3]
        try: memory=int(mem.replace('MiB','').strip())
        except (ValueError,TypeError):continue
        if memory>0 and process_hint.lower() in process.lower():
            result.append({'pid':pid,'process':process,'gpu_memory_mib':memory})
    return result


def verify(iterations=10,hint='ollama'):
    mode=os.getenv('AQ_MODE','deterministic')
    if mode=='ollama':
        configured_url=os.getenv('AQ_OLLAMA_URL','http://127.0.0.1:11434')
    elif mode=='nim' and os.getenv('AQ_NIM_SELFHOSTED_ATTESTED')=='1':
        configured_url=os.getenv('AQ_NIM_BASE_URL','')
    elif mode=='openai_compatible' and os.getenv('AQ_LOCAL_BACKEND_ATTESTED')=='1':
        configured_url=os.getenv('AQ_OPENAI_BASE_URL','')
    else:
        raise RuntimeError('Requires a local Ollama model or explicitly attested self-hosted accelerator/compatible model')
    address=urlparse(configured_url)
    if address.hostname not in ('127.0.0.1','localhost','::1'):
        raise RuntimeError('Inference endpoint must be localhost on the accelerator GPU machine; hosted NIM cannot prove local GPU usage')
    if iterations<2 or iterations>100:raise ValueError('iterations must be in 2..100')
    probe=subprocess.run(['nvi' + 'dia-smi','-L'],capture_output=True,text=True,timeout=10,check=True)
    stop=threading.Event()
    seen=[]
    errors=[]
    def collect():
        while not stop.is_set():
            try:
                result=subprocess.run(['nvi' + 'dia-smi','--query-compute-apps=pid,process_name,used_gpu_memory','--format=csv,noheader,nounits'],
                                      capture_output=True,text=True,timeout=5,check=True)
                seen.extend(parse_compute_processes(result.stdout,hint))
            except Exception as exc:
                errors.append(type(exc).__name__)
            stop.wait(0.15)
    watcher=threading.Thread(target=collect,daemon=True)
    watcher.start()
    records=[]
    try:
        runner=AgentRunner()
        for n in range(iterations):
            result=runner.triage(TriageRequest(incident_id=f'GPU-RESIDENCY-{n}',message='Database query failed'))
            records.append({'model_used':result.model_used,'fallback_used':result.fallback_used,
                            'latency_ms':result.latency_ms})
    finally:
        stop.set()
        watcher.join(timeout=8)
    report={'timestamp':datetime.now(timezone.utc).isoformat(),'host_gpu_list':probe.stdout.strip(),
            'mode':os.getenv('AQ_MODE'),'model':runner.model.model,'requests':len(records),
            'model_used_count':sum(r['model_used'] for r in records),
            'fallback_count':sum(r['fallback_used'] for r in records),
            'gpu_process_hint':hint,'matching_gpu_compute_process_samples':len(seen),
            'max_matching_gpu_process_memory_mib':max((r['gpu_memory_mib'] for r in seen),default=0),
            'sampler_errors':errors[:3],
            'limitations':'Local process memory overlap provides stronger local attribution but does not prove which exact kernels each request executed. Validate dedicated GPU service logs. Do not use for hosted remote NIM.'}
    report['gate_passed']=bool(all(r['model_used'] and not r['fallback_used'] for r in records) and seen)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iterations',type=int,default=10)
    parser.add_argument('--process-hint',default=os.getenv('AQ_GPU_PROCESS_HINT','ollama'))
    parser.add_argument('--out',default='artifacts/gpu-residency-report.json')
    args=parser.parse_args()
    result=verify(args.iterations,args.process_hint)
    destination=Path(args.out)
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    if not result['gate_passed']:raise SystemExit('GPU inference residency NOT demonstrated')

if __name__=='__main__':main()
