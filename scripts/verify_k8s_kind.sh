#!/usr/bin/env bash
# Test REAL containers in an isolated disposable kind cluster; do not touch the active kubeconfig.
set -euo pipefail
cd "$(dirname "$0")/.."
for bin in docker kind kubectl python3; do
  command -v "$bin" >/dev/null || { echo "Missing $bin" >&2; exit 2; }
done
docker info >/dev/null || { echo 'Docker daemon is not running' >&2; exit 2; }
NAME="${AQ_KIND_NAME:-aq-reliability-test}"
[[ "$NAME" =~ ^[a-z][a-z0-9-]{0,35}$ ]] || { echo 'Invalid AQ_KIND_NAME' >&2; exit 2; }
if kind get clusters | grep -Fxq "$NAME"; then
  echo "Cluster '$NAME' already exists; refusing to change it" >&2; exit 2
fi
WORKDIR="$(mktemp -d)"
CREATED=0
SUCCESS=0
cleanup() {
  local cleanup_ok=0
  [[ -z "${PF_PID:-}" ]] || kill "$PF_PID" 2>/dev/null || true
  if (( CREATED == 1 )); then
    if kind delete cluster --name "$NAME"; then cleanup_ok=1; fi
  fi
  if (( SUCCESS == 1 )); then
    python3 - "$cleanup_ok" <<'PY'
import json,sys
from pathlib import Path
path=Path('artifacts/k8s/kind-verification.json')
report=json.loads(path.read_text())
report['kind_cluster_deleted_after_test']=bool(int(sys.argv[1]))
report['verified']=bool(report['verified'] and report['kind_cluster_deleted_after_test'])
path.write_text(json.dumps(report,indent=2)+'\n')
PY
  fi
  rm -rf "$WORKDIR"
}
trap cleanup EXIT
export KUBECONFIG="$WORKDIR/kubeconfig"
# Mark ownership of previously nonexistent cluster before creating it, for partial-failure cleanup.
CREATED=1
kind create cluster --name "$NAME" --wait 180s --kubeconfig "$KUBECONFIG"
CONTEXT="kind-$NAME"
docker build -t agentic-quality-reliability-lab:local .
kind load docker-image agentic-quality-reliability-lab:local --name "$NAME"
kubectl --context "$CONTEXT" apply -f k8s/deployment.yaml
kubectl --context "$CONTEXT" rollout status deployment/agent-quality-lab --timeout=240s
kubectl --context "$CONTEXT" wait --for=condition=Ready pod -l app=agent-quality-lab --timeout=180s
kubectl --context "$CONTEXT" get pods -l app=agent-quality-lab -o json > "$WORKDIR/pods-before.json"
OLD_POD="$(python3 - "$WORKDIR/pods-before.json" <<'PY'
import json,sys
pods=json.load(open(sys.argv[1]))['items']
assert len(pods)==2, f'expected 2 pods; got {len(pods)}'
assert all(p['status']['phase']=='Running' for p in pods)
print(sorted(p['metadata']['name'] for p in pods)[0])
PY
)"
# Delete ONE actual application pod and verify the Deployment controller recreates it.
kubectl --context "$CONTEXT" delete pod "$OLD_POD" --wait=false
kubectl --context "$CONTEXT" rollout status deployment/agent-quality-lab --timeout=240s
# Do not mistake a completed rollout status observed during termination for pod recreation.
RECOVERED=0
for _ in $(seq 1 60); do
  kubectl --context "$CONTEXT" get pods -l app=agent-quality-lab -o json > "$WORKDIR/pods-after.json"
  if python3 - "$WORKDIR/pods-after.json" "$OLD_POD" <<'PY_WAIT'
import json,sys
p=json.load(open(sys.argv[1]))['items']
assert len(p)==2
assert sys.argv[2] not in {x['metadata']['name'] for x in p}
assert all(x['status']['phase']=='Running' and any(
    c['type']=='Ready' and c['status']=='True' for c in x['status'].get('conditions',[])
) for x in p)
PY_WAIT
  then
    RECOVERED=1
    break
  fi
  sleep 3
done
[[ "$RECOVERED" == 1 ]] || { echo 'Two replacement Ready pods not observed' >&2; exit 1; }
kubectl --context "$CONTEXT" port-forward service/agent-quality-lab 18080:8000 > "$WORKDIR/port-forward.log" 2>&1 &
PF_PID=$!
python3 - "$WORKDIR/pods-before.json" "$WORKDIR/pods-after.json" "$OLD_POD" <<'PY'
import json,sys,time,urllib.request
from pathlib import Path
before=json.loads(Path(sys.argv[1]).read_text())['items']
after=json.loads(Path(sys.argv[2]).read_text())['items']
assert len(after)==2 and all(p['status']['phase']=='Running' for p in after)
assert sys.argv[3] not in {p['metadata']['name'] for p in after}, 'deleted pod still present'
for _ in range(60):
    try:
        with urllib.request.urlopen('http://127.0.0.1:18080/api/health', timeout=3) as h:
            assert json.load(h)['status']=='ok'
        break
    except (OSError,AssertionError): time.sleep(1)
else: raise SystemExit('kind service HTTP health did not respond')
print('Verified two real pods, real pod replacement, and live service HTTP')
PY
mkdir -p artifacts/k8s
cp "$WORKDIR/pods-before.json" artifacts/k8s/kind-pods-before.json
cp "$WORKDIR/pods-after.json" artifacts/k8s/kind-pods-after.json
python3 - <<'PY'
import json
from datetime import datetime,timezone
from pathlib import Path
Path('artifacts/k8s/kind-verification.json').write_text(json.dumps({
  'verified':True, 'kind_cluster_deleted_after_test':False,
  'checks':{'docker_image_built':True,'two_real_pods_ready':True,
            'deleted_pod_recreated':True,'service_health_http':True},
  'generated_at':datetime.now(timezone.utc).isoformat(),
  'scope':'Actual kind application container execution and pod replacement, not KWOK fake pods'
},indent=2)+'\n')
PY
SUCCESS=1
