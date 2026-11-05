"""Offline checks for the Docker-first Mac user path; NOT live container proof."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_docker_first_launcher_and_service_paths_are_present():
    launcher = (ROOT/'start-docker.sh').read_text()
    compose = (ROOT/'docker-compose.yml').read_text()
    assert 'docker info' in launcher
    assert 'docker compose version' in launcher
    assert 'scripts/verify_docker_stack.sh' in launcher
    for service in ('app:', 'prometheus:', 'grafana:'):
        assert service in compose
    for port in ('127.0.0.1:8000:8000', '127.0.0.1:9090:9090', '127.0.0.1:3000:3000'):
        assert port in compose
    for file in ('observability/prometheus.yml',
                 'observability/grafana/provisioning/datasources/datasource.yml',
                 'observability/grafana/dashboards/agent-quality.json'):
        assert (ROOT/file).is_file()
