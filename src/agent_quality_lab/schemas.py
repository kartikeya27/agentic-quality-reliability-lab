from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

Category = Literal["identity", "database", "deployment", "network", "general"]
Severity = Literal["critical", "high", "medium"]
Fault = Literal["none", "tool_error", "timeout", "slow_tool"]

class TriageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incident_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    message: str = Field(min_length=1, max_length=4000)
    fault: Fault = "none"

class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Category
    severity: Severity

class ToolTrace(BaseModel):
    tool: Literal["lookup_runbook"]
    status: Literal["ok", "error", "timeout"]
    runbook_id: str | None = None

class TriageResult(BaseModel):
    incident_id: str
    category: Category
    severity: Severity
    team: str
    runbook_id: str
    steps: list[str]
    trace: list[ToolTrace]
    mode: str
    model_used: bool
    fallback_used: bool
    degraded: bool
    latency_ms: float = Field(ge=0)

class GoldCase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    message: str
    expected_category: Category
    expected_severity: Severity
    tags: list[str] = Field(min_length=1)
