#!/usr/bin/env bash
# Optional: real authorized NIM-compatible inference. No credentials saved to artifacts.
set -euo pipefail
cd "$(dirname "$0")/.."
[[ -n "${AQ_NIM_BASE_URL:-}" && -n "${AQ_NIM_MODEL:-}" && "${AQ_NIM_MODEL:-}" != your-deployed-nim-model-id ]] || {
  echo 'Configure AQ_NIM_BASE_URL and AQ_NIM_MODEL for a real, authorized service.' >&2; exit 2;
}
[[ "${AQ_NIM_AUTHORIZED:-0}" == 1 ]] || {
  echo 'Set AQ_NIM_AUTHORIZED=1 after confirming access and service identity; generic compatible APIs are not NIM proof.' >&2; exit 2;
}
python - <<'PY_CHECK'
import os,sys
from urllib.parse import urlparse
url=os.environ['AQ_NIM_BASE_URL']
p=urlparse(url)
if p.scheme not in ('http','https') or not p.hostname:
    sys.exit('Invalid AQ_NIM_BASE_URL')
if p.scheme != 'https' and p.hostname not in ('127.0.0.1','localhost','::1'):
    sys.exit('Remote inference requires HTTPS')
print('Endpoint and explicit operator authorization accepted; live responses are checked next.')
PY_CHECK
export AQ_MODE=nim
python -m agent_quality_lab.readiness --probe-model --require-model --out artifacts/nim-readiness.json
python -m agent_quality_lab eval --min-pass-rate 0 --require-model --out artifacts/nim-eval.json
python -m agent_quality_lab advanced --min-pass-rate 0 --require-model --out artifacts/nim-advanced.json
python -m agent_quality_lab model-experiment --out artifacts/nim-vs-baseline.json
printf 'Live HTTP inference verified. Service identity remains operator-attested.\n'
