"""Main FastAPI application for AgentBazaar."""

import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.engine import execute_agent_capability, run_orchestration
from app.manifest import fetch_and_discover, generate_agent_network_manifest
from app.models import AgentCreate, AgentDetail, InvokeRequest, InvokeResponse, RunCreate
from app.registry import AgentRegistry

app = FastAPI(
    title="AgentBazaar API",
    description="Open Agentic Web marketplace and trust registry for autonomous agents",
    version="0.1.0",
)

# Enable CORS for open agentic web interactions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = AgentRegistry()

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/.well-known/agent-network.json")
def get_manifest(request: Request):
    base_url = str(request.base_url).rstrip("/")
    agents = registry.list_agents()
    manifest_data = generate_agent_network_manifest(agents, base_url=base_url)
    return JSONResponse(
        content=manifest_data,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )


@app.get("/api/agents")
def list_agents(
    capability: Optional[str] = Query(None, description="Filter by capability name"),
    q: Optional[str] = Query(None, description="Search query string"),
):
    agents = registry.list_agents(capability=capability, q=q)
    return {
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "description": a.description,
                "capabilities": a.capabilities,
                "endpoint": a.endpoint,
                "price_range": a.price_range,
                "hours": a.hours,
                "trust_score": a.trust_score,
                "calls_total": a.calls_total,
                "calls_ok": a.calls_ok,
                "p50_latency_ms": a.p50_latency_ms,
            }
            for a in agents
        ]
    }


@app.post("/api/agents", status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, request: Request):
    agent = registry.create_agent(payload)
    if not agent:
        raise HTTPException(status_code=500, detail="Failed to create agent")
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "capabilities": agent.capabilities,
        "endpoint": agent.endpoint,
        "price_range": agent.price_range,
        "hours": agent.hours,
        "trust_score": agent.trust_score,
        "trust_breakdown": agent.trust_breakdown.model_dump(),
        "calls_total": agent.calls_total,
        "calls_ok": agent.calls_ok,
        "p50_latency_ms": agent.p50_latency_ms,
    }


@app.get("/api/agents/{agent_id}")
def get_agent_detail(agent_id: str):
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "capabilities": agent.capabilities,
        "endpoint": agent.endpoint,
        "price_range": agent.price_range,
        "hours": agent.hours,
        "trust_score": agent.trust_score,
        "trust_breakdown": agent.trust_breakdown.model_dump(),
        "calls_total": agent.calls_total,
        "calls_ok": agent.calls_ok,
        "p50_latency_ms": agent.p50_latency_ms,
    }


@app.post("/api/agents/{agent_id}/invoke")
def invoke_agent(agent_id: str, payload: InvokeRequest):
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    ok, latency_ms, result, err = execute_agent_capability(
        agent=agent, capability=payload.capability, params=payload.params
    )

    # Record invocation and update trust stats
    registry.record_invocation(agent_id=agent_id, ok=ok, latency_ms=latency_ms)

    return {
        "agent_id": agent_id,
        "capability": payload.capability,
        "ok": ok,
        "latency_ms": latency_ms,
        "result": result,
        "error": err,
    }


@app.get("/api/discover")
def discover_external_agents(url: str = Query(..., description="Target site URL")):
    result = fetch_and_discover(url)
    return result


@app.post("/api/runs", status_code=status.HTTP_201_CREATED)
def create_run(payload: RunCreate):
    run = run_orchestration(
        registry=registry, scenario=payload.scenario, input_data=payload.input
    )
    return {
        "run_id": run.run_id,
        "scenario": run.scenario,
        "status": run.status,
        "steps_count": len(run.steps),
        "steps": [s.model_dump() for s in run.steps],
        "result": run.result,
        "created_at": run.created_at,
    }


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = registry.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {
        "run_id": run.run_id,
        "scenario": run.scenario,
        "input": run.input,
        "status": run.status,
        "steps": [s.model_dump() for s in run.steps],
        "result": run.result,
        "created_at": run.created_at,
    }


@app.post("/api/reset")
def reset_demo_data():
    registry.reset_to_seeds()
    return {"ok": True, "message": "Demo agents and statistics reset to seed data."}


# Serve root index.html
@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return {"message": "AgentBazaar is running. Please add static/index.html"}


# Mount static directory if it exists
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
