#!/usr/bin/env python3
"""Start a real local API, execute bounded HTTP load, evaluate explicit SLOs."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from agent_quality_lab.performance import run_load
from agent_quality_lab.slo import evaluate_slo


def verify() -> dict:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, AQ_MODE="deterministic", AQ_ENABLE_FAULTS="0")
    child = subprocess.Popen([sys.executable, "-m", "agent_quality_lab", "serve", "--port", str(port)],
                             env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}"
    try:
        for _ in range(60):
            if child.poll() is not None:
                raise RuntimeError("Local API exited before load test")
            try:
                if httpx.get(url + "/api/health", timeout=1).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        else:
            raise RuntimeError("Local API not ready")
        load = run_load(url, requests=30, concurrency=4)
        gate = evaluate_slo(load, max_p95_ms=10000, max_p99_ms=12000,
                            max_error_rate=0, min_throughput_rps=0.1, min_requests=30)
        target = Path("artifacts")
        target.mkdir(exist_ok=True)
        (target / "slo-load-report.json").write_text(json.dumps(load, indent=2) + "\n")
        (target / "slo-gate-report.json").write_text(json.dumps(gate, indent=2) + "\n")
        return gate
    finally:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


if __name__ == "__main__":
    result = verify()
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit("Observed local HTTP SLO failed")
