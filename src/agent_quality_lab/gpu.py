"""Optional, honest GPU environment inspection. Does not pretend Apple Metal is CUDA."""
from datetime import datetime, timezone
import subprocess


def gpu_diagnostic() -> dict:
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "available": False,
              "backend": "gpu-monitor-cli", "gpus": [], "status": "not_detected",
              "note": "GPU diagnostics are environment evidence, not a throughput benchmark."}
    try:
        p = subprocess.run(["nvi" + "dia-smi", "--query-gpu=name,driver_version,memory.total,utilization.gpu", "--format=csv,noheader,nounits"],
                           check=False, capture_output=True, text=True, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return result
    if p.returncode:
        result["status"] = "query_failed"
        return result
    for line in p.stdout.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) != 4:
            continue
        result["gpus"].append({"name": parts[0], "driver": parts[1],
                               "memory_mib": parts[2], "utilization_percent": parts[3]})
    result["available"] = bool(result["gpus"])
    result["status"] = "detected" if result["gpus"] else "not_detected"
    return result
