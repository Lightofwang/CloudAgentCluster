"""Main FastAPI application entrypoint for DraftLens."""

from __future__ import annotations

import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.db import init_db
from app.routers.teams import router as teams_router
from app.routers.scout import router as scout_router
from app.routers.draft import router as draft_router

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schema on start
    init_db()
    yield


app = FastAPI(
    title="DraftLens API",
    description="Macro Scouting & Fearless Draft Management System",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(teams_router, prefix="/api", tags=["Teams & Players"])
app.include_router(scout_router, prefix="/api", tags=["Scouting"])
app.include_router(draft_router, prefix="/api", tags=["Draft Simulator"])


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/grid/status")
def grid_status():
    return {
        "mode": "sample-data",
        "grid_connected": False,
        "note": "Sample benchmark dataset loaded locally; GRID integration optional",
    }


# Mount static assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "DraftLens API is running. Static frontend not yet compiled."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
