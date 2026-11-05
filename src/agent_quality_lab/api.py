"""Local demo API. Expose only to a trusted environment."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, HTMLResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from .agent import AgentRunner
from .schemas import TriageRequest, TriageResult
from .tools import RUNBOOKS
from .qa_metrics import load_metrics
from .local_dashboard import HTML, collect_evidence


def create_app(runner: AgentRunner | None = None) -> FastAPI:
    app = FastAPI(title="Agentic Quality & Reliability Lab", version="0.5.0")
    engine = runner or AgentRunner()

    @app.get("/dashboard", response_class=HTMLResponse)
    def dashboard():
        return HTML

    @app.get("/api/evidence")
    def evidence():
        return collect_evidence()

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mode": engine.model.mode, "model": engine.model.model, "note": "Process health only; not an inference availability check"}

    @app.get("/api/runbooks")
    def runbooks():
        return {key: {"id": value["id"], "team": value["team"]} for key, value in RUNBOOKS.items()}

    @app.post("/api/triage", response_model=TriageResult)
    def triage(request: TriageRequest):
        if request.fault != "none" and os.getenv("AQ_ENABLE_FAULTS", "0") != "1":
            raise HTTPException(status_code=403, detail="Fault injection disabled. Set AQ_ENABLE_FAULTS=1 in a local demo only.")
        return engine.triage(request)

    @app.get("/metrics")
    def metrics():
        load_metrics(os.getenv("AQ_ARTIFACT_DIR", "artifacts"))
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app

app = create_app()
