"""Data models for AgentBazaar."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TrustBreakdown(BaseModel):
    verifiable: int = Field(default=30, ge=0, le=30, description="Manifest and domain verification (0-30)")
    success_rate: int = Field(default=40, ge=0, le=40, description="Call success rate (0-40)")
    latency: int = Field(default=30, ge=0, le=30, description="p50 latency score (0-30)")


class Agent(BaseModel):
    id: str
    name: str
    description: str
    capabilities: List[str]
    endpoint: str
    price_range: str = "¥50–¥500"
    hours: str = "09:00–21:00"
    trust_score: int = 100
    trust_breakdown: TrustBreakdown = Field(default_factory=TrustBreakdown)
    calls_total: int = 0
    calls_ok: int = 0
    p50_latency_ms: int = 150
    latencies: List[int] = Field(default_factory=list)


class AgentCreate(BaseModel):
    name: str
    description: str
    capabilities: List[str]
    price_range: Optional[str] = "¥50–¥500"
    hours: Optional[str] = "09:00–21:00"
    endpoint: Optional[str] = None


class AgentSummary(BaseModel):
    id: str
    name: str
    description: str
    capabilities: List[str]
    endpoint: str
    price_range: str
    hours: str
    trust_score: int
    calls_total: int
    calls_ok: int
    p50_latency_ms: int


class AgentDetail(BaseModel):
    id: str
    name: str
    description: str
    capabilities: List[str]
    endpoint: str
    price_range: str
    hours: str
    trust_score: int
    trust_breakdown: Dict[str, int]
    calls_total: int
    calls_ok: int
    p50_latency_ms: int


class InvokeRequest(BaseModel):
    capability: str
    params: Dict[str, Any] = Field(default_factory=dict)


class InvokeResponse(BaseModel):
    agent_id: str
    capability: str
    ok: bool
    latency_ms: int
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class RunStep(BaseModel):
    step: int
    agent_id: str
    action: str
    status: str  # "success", "failed", "running"
    detail: Any
    latency_ms: int
    timestamp: str


class RunCreate(BaseModel):
    scenario: str  # "compare-price", "track-order", "book-appointment"
    input: Dict[str, Any] = Field(default_factory=dict)


class Run(BaseModel):
    run_id: str
    scenario: str
    input: Dict[str, Any]
    status: str  # "completed", "failed", "in_progress"
    steps: List[RunStep] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    created_at: str
