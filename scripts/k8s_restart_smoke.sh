#!/usr/bin/env bash
# Real-cluster deployment resilience smoke check, not simulated KWOK infrastructure.
set -euo pipefail
kubectl rollout status deployment/agent-quality-lab --timeout=90s
kubectl rollout restart deployment/agent-quality-lab
kubectl rollout status deployment/agent-quality-lab --timeout=120s
kubectl get deployment agent-quality-lab
printf '\nRestart smoke test complete. Review rollout availability and pod events.\n'
