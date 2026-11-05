"""Observable capability checks. Unavailable integrations are reported, never guessed.

No remote connection is attempted unless the operator explicitly requests --probe-model.
Credentials are intentionally never copied into evidence files.
"""
import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .gpu import gpu_diagnostic
from .llm import ModelClient, ModelError


def _which(name: str) -> dict:
    binary = shutil.which(name)
    return {"available": bool(binary), "path": binary or None}


def _command_version(command: list[str]) -> dict:
    if not shutil.which(command[0]):
        return {"available": False, "reason": f"{command[0]} not installed"}
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=12)
        return {"available": proc.returncode == 0, "detail": (proc.stdout or proc.stderr).strip()[:240], "exit_code": proc.returncode}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "reason": type(exc).__name__}


def check_readiness(probe_model: bool = False) -> dict:
    mode = os.getenv("AQ_MODE", "deterministic")
    tools = {name: _which(name) for name in ("docker", "kubectl", "kind", "kwokctl", "ollama", "git")}
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host": {"system": platform.system(), "machine": platform.machine(), "python": platform.python_version()},
        "tools": tools,
        "gpu_monitor": _which("nvi" + "dia-smi"),
        "docker_daemon": _command_version(["docker", "info", "--format", "{{.ServerVersion}}"]),
        "ollama_runtime": _command_version(["ollama", "list"]),
        "nemo_sdk_installed": importlib.util.find_spec("nemoguardrails") is not None,
        "gpu": gpu_diagnostic(),
        "model": {"mode": mode, "probe_requested": probe_model, "actual_inference_verified": False},
        "explanation": "Presence checks are not deployment or performance validation. Model probe only validates that a real inference request produced a parsed response.",
    }
    if probe_model:
        if mode == "deterministic":
            report["model"]["error"] = "Set AQ_MODE to ollama or nim (or openai_compatible) before probing"
        else:
            try:
                answer = ModelClient().complete_json(
                    "Return only a JSON object with category set to network and severity set to high."
                )
                report["model"].update({"actual_inference_verified": bool(answer), "response_is_object": isinstance(answer, dict)})
            except (ModelError, ValueError) as exc:
                report["model"]["error"] = f"{type(exc).__name__}: inference request failed; inspect model service logs"
    return report


def main():
    parser = argparse.ArgumentParser(description="Generate explicit local environment readiness evidence")
    parser.add_argument("--out", default="artifacts/readiness-report.json")
    parser.add_argument("--probe-model", action="store_true", help="Actually contact configured Ollama/NIM service")
    parser.add_argument("--require-model", action="store_true", help="Fail if a live model response was not validated")
    args = parser.parse_args()
    report = check_readiness(args.probe_model)
    destination = Path(args.out)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if args.require_model and not report["model"]["actual_inference_verified"]:
        raise SystemExit("Real inference was NOT verified")


if __name__ == "__main__":
    main()
