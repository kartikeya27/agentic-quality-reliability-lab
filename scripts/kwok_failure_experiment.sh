#!/usr/bin/env bash
# Creates ONLY a new isolated KWOK cluster; never runs against the current kubectl context.
# Needs kwokctl, kubectl, Docker Desktop. Docker Desktop != Docker Kubernetes.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
for bin in kwokctl kubectl python3; do command -v "$bin" >/dev/null || { echo "Missing $bin" >&2; exit 2; }; done
NAME="${AQ_KWOK_NAME:-aq-lab}"
NODES="${AQ_KWOK_NODES:-4}"
REPLICAS="${AQ_KWOK_REPLICAS:-60}"
if [[ ! "$NODES" =~ ^[0-9]+$ || ! "$REPLICAS" =~ ^[0-9]+$ ]] || (( NODES < 2 || NODES > 20 || REPLICAS < 2 || REPLICAS > 500 )); then
  echo "Allowed simulation scale: NODES 2..20; REPLICAS 2..500" >&2; exit 2
fi
mkdir -p artifacts/kwok
KUBECONFIG_LOCAL="$(mktemp)"
CREATED=0
cleanup() {
  rm -f "$KUBECONFIG_LOCAL"
  if (( CREATED == 1 )) && [[ "${AQ_KWOK_KEEP_CLUSTER:-0}" != "1" ]]; then
    kwokctl delete cluster --name "$NAME" || true
  fi
}
trap cleanup EXIT
# Abort if this name already exists: do not modify a cluster belonging to someone else.
if kwokctl get clusters 2>/dev/null | grep -Fxq "$NAME"; then
  echo "KWOK cluster '$NAME' already exists. Choose a new AQ_KWOK_NAME to avoid modifying it." >&2; exit 2
fi
kwokctl create cluster --name "$NAME" --runtime docker --kubeconfig "$KUBECONFIG_LOCAL" --wait 180s
CREATED=1
kwokctl get kubeconfig --name "$NAME" > "$KUBECONFIG_LOCAL"
kub() { kubectl --kubeconfig "$KUBECONFIG_LOCAL" "$@"; }
kub create namespace aq-kwok-lab
kwokctl scale node --name "$NAME" --replicas "$NODES"
# Explicit tolerance allows scheduling onto KWOK's fake nodes.
cat > artifacts/kwok/deployment.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: qa-fake
  namespace: aq-kwok-lab
spec:
  replicas: $REPLICAS
  selector:
    matchLabels: {app: qa-fake}
  template:
    metadata:
      labels: {app: qa-fake}
    spec:
      tolerations:
      - key: kwok.x-k8s.io/node
        operator: Exists
        effect: NoSchedule
      containers:
      - name: fake
        image: registry.invalid/kwok-no-container-is-executed:example
        resources:
          requests: {cpu: 10m, memory: 4Mi}
EOF
kub apply -f artifacts/kwok/deployment.yaml
kub -n aq-kwok-lab rollout status deployment/qa-fake --timeout=180s
kub get nodes -o json > artifacts/kwok/nodes-before.json
kub -n aq-kwok-lab get pods -o json > artifacts/kwok/pods-before.json
# Deterministic target from snapshots rather than arbitrary current-context access.
DELETED_NODE="$(python3 - <<'PY'
import json
r=json.load(open('artifacts/kwok/nodes-before.json'))
print(sorted(x['metadata']['name'] for x in r['items'])[0])
PY
)"
echo "Inject node-loss condition: delete virtual node $DELETED_NODE"
kub delete node "$DELETED_NODE" --wait=true
# Controlled remediation of affected virtual pods: explicit deletion, not automatic
# real-world recovery. A KWOK fake pod will not independently drain/restart.
while IFS= read -r affected_pod; do
  [[ -n "$affected_pod" ]] || continue
  kub -n aq-kwok-lab delete pod "$affected_pod" --wait=false
done < <(python3 - "$DELETED_NODE" <<'PY_SELECT'
import json, sys
r=json.load(open('artifacts/kwok/pods-before.json'))
for item in r['items']:
    if item.get('spec', {}).get('nodeName') == sys.argv[1]:
        print(item['metadata']['name'])
PY_SELECT
)
# Request new pods so scheduler has fresh work following the simulated failure.
NEW_REPLICAS=$((REPLICAS + 3))
kub -n aq-kwok-lab scale deployment/qa-fake --replicas "$NEW_REPLICAS"
# Give the scheduler a chance to place the new pods; do not assert recovery of fake workloads.
kub -n aq-kwok-lab rollout status deployment/qa-fake --timeout=180s
kub get nodes -o json > artifacts/kwok/nodes-after.json
kub -n aq-kwok-lab get pods -o json > artifacts/kwok/pods-after.json
python3 - "$DELETED_NODE" "$NEW_REPLICAS" <<'PY'
import json, sys
from pathlib import Path
from agent_quality_lab.kwok_report import build_report
result = build_report('artifacts/kwok', sys.argv[1], int(sys.argv[2]))
Path('artifacts/kwok/kwok-report.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
if not result['passed']:
    sys.exit('KWOK scheduling gate failed')
PY
