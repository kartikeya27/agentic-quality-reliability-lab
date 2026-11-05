.PHONY: install test eval chaos generate flaky select serve observability advanced inference-chaos efficiency gpu-diag
install:
	python -m pip install -e '.[dev]'
test:
	python -m pytest -q
eval:
	python -m agent_quality_lab eval
chaos:
	python -m agent_quality_lab chaos
generate:
	python -m agent_quality_lab generate
flaky:
	python -m agent_quality_lab flaky
select:
	python -m agent_quality_lab select --budget 6
serve:
	python -m agent_quality_lab serve
observability:
	docker compose up --build -d
advanced:
	python -m agent_quality_lab advanced
inference-chaos:
	python -m agent_quality_lab inference-chaos
efficiency:
	python -m agent_quality_lab efficiency
gpu-diag:
	python -m agent_quality_lab gpu-diag

.PHONY: verify verify-docker verify-kind verify-ollama verify-nim verify-nemo verify-kwok
verify:
	bash scripts/verify_local.sh
verify-docker:
	bash scripts/verify_docker_stack.sh
verify-kind:
	bash scripts/verify_k8s_kind.sh
verify-ollama:
	bash scripts/verify_ollama_live.sh
verify-nim:
	bash scripts/verify_nim_live.sh
verify-nemo:
	bash scripts/verify_nemo_live.sh
verify-kwok:
	bash scripts/kwok_failure_experiment.sh
.PHONY: verify-gpu mutation
verify-gpu:
	bash scripts/verify_gpu_nim.sh
mutation:
	python -m agent_quality_lab mutation --budget 6


.PHONY: verify-backend-contract audit-integrations audit-strict
verify-backend-contract:
	python scripts/verify_backend_http_contract.py
audit-integrations:
	python scripts/audit_integrations.py
audit-strict:
	python scripts/audit_integrations.py --strict

.PHONY: verify-slo traceability bug-cycle
verify-slo:
	python scripts/verify_perf_slo.py
traceability:
	python -m agent_quality_lab traceability
bug-cycle:
	python -m agent_quality_lab bug-cycle

# End-to-end evidence: verified / blocked / failed; no mocked live success.
.PHONY: verify-everything verify-everything-strict verify-ci productivity-template productivity-report
verify-everything:
	python scripts/verify_everything.py
verify-everything-strict:
	python scripts/verify_everything.py --strict
verify-ci:
	python scripts/verify_github_actions.py
productivity-template:
	python scripts/productivity_experiment.py --template
productivity-report:
	python scripts/productivity_experiment.py

# One-command local demo; does NOT install or run external platforms.
.PHONY: demo demo-check
demo:
	bash run-local.sh
demo-check:
	python scripts/run_local_demo.py

# Docker Desktop is already installed: build + test + check the live monitoring stack.
.PHONY: docker-demo docker-stop docker-status
docker-demo:
	bash start-docker.sh
docker-stop:
	docker compose down
docker-status:
	docker compose ps
