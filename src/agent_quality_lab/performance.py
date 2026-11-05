"""Lightweight, bounded local HTTP load driver. Not a substitute for k6/Locust."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import httpx
from .evaluation import percentile


def run_load(url: str, requests: int = 30, concurrency: int = 5) -> dict:
    if not (1 <= requests <= 1000 and 1 <= concurrency <= 50):
        raise ValueError("Load limits: 1<=requests<=1000 and 1<=concurrency<=50")
    if not url.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise ValueError("For safety, this demo load tool only supports localhost URLs")
    def call(i: int) -> dict:
        started = time.perf_counter()
        try:
            with httpx.Client(timeout=15) as client:
                response = client.post(url.rstrip("/") + "/api/triage", json={"incident_id": f"PERF-{i}", "message": "DNS lookup error on test service"})
            return {"status": response.status_code, "latency_ms": (time.perf_counter()-started)*1000}
        except httpx.RequestError:
            return {"status": 0, "latency_ms": (time.perf_counter()-started)*1000}
    begin = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        results = [future.result() for future in as_completed([pool.submit(call, i) for i in range(requests)])]
    total_seconds = time.perf_counter() - begin
    latencies = [r["latency_ms"] for r in results]
    good = sum(r["status"] == 200 for r in results)
    return {"requests": requests, "concurrency": concurrency, "successful": good,
            "failed": requests-good, "throughput_rps": round(requests/total_seconds, 2),
            "p50_ms": round(percentile(latencies, .5), 2), "p95_ms": round(percentile(latencies, .95), 2),
            "p99_ms": round(percentile(latencies, .99), 2), "total_seconds": round(total_seconds, 3),
            "note": "Client-observed local benchmark; results depend on machine and inference mode."}
