"""Opt-in *real* NeMo Guardrails SDK smoke test, not a mocked integration.

The external optional package and local Ollama runtime are required to execute.
"""
from datetime import datetime, timezone
from pathlib import Path


def run_nemo_smoke(config_dir="nemo/guardrails", prompt="The DNS service has packet loss", *, rails_factory=None) -> dict:
    if rails_factory is None:
        try:
            from nemoguardrails import LLMRails, RailsConfig
        except ImportError as exc:
            raise RuntimeError("NeMo Guardrails is optional. Install with: pip install -e '.[nemo]'") from exc
        rails = LLMRails(RailsConfig.from_path(str(Path(config_dir))))
    else:
        rails = rails_factory(config_dir)
    result = rails.generate(messages=[{"role": "user", "content": prompt}])
    content = result.get("content", "") if isinstance(result, dict) else str(result)
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "sdk_executed": True,
            "content": str(content)[:2000],
            "note": "SDK smoke response only. NeMo policy effectiveness is not guaranteed or scored by this command."}
