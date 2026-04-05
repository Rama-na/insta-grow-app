"""
REST + WebSocket endpoints for simulation jobs.

POST /api/jobs            → create and start a job
GET  /api/jobs/{id}       → poll job state
GET  /api/jobs/{id}/stl   → download baseline or optimised STL
WS   /api/jobs/{id}/ws    → stream real-time progress
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from app.models.schemas import (
    SimulationJobRequest, JobCreatedResponse, JobState, JobStatus,
)
from app.services.job_service import create_job, get_job, get_queue, run_job
from app.core.config import settings

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _serialise(obj):
    """JSON-safe serialisation for Pydantic models."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return str(obj)


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=JobCreatedResponse)
async def create_simulation_job(request: SimulationJobRequest):
    job_id = create_job(request)
    asyncio.create_task(run_job(job_id, request))
    return JobCreatedResponse(
        job_id=job_id,
        status=JobStatus.pending,
        message="Job queued. Connect to /api/jobs/{id}/ws for live updates.",
    )


@router.get("/{job_id}", response_model=JobState)
async def get_job_state(job_id: str):
    state = get_job(job_id)
    if not state:
        raise HTTPException(404, f"Job '{job_id}' not found.")
    return state


@router.get("/{job_id}/stl/{variant}")
async def download_stl(job_id: str, variant: str = "baseline"):
    if variant not in ("baseline", "optimised"):
        raise HTTPException(400, "variant must be 'baseline' or 'optimised'.")
    path = settings.jobs_dir / job_id / f"{variant}.stl"
    if not path.exists():
        raise HTTPException(404, f"STL file not found yet for job '{job_id}'.")
    return FileResponse(str(path), media_type="model/stl", filename=f"{variant}.stl")


@router.websocket("/{job_id}/ws")
async def job_websocket(websocket: WebSocket, job_id: str):
    await websocket.accept()
    state = get_job(job_id)
    if not state:
        await websocket.send_text(json.dumps({"error": f"Job {job_id} not found"}))
        await websocket.close()
        return

    # Send current state immediately on connect
    await websocket.send_text(json.dumps(state.model_dump(), default=_serialise))

    q = get_queue(job_id)
    if not q:
        await websocket.close()
        return

    try:
        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=30)
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text(json.dumps({"heartbeat": True}))
                continue

            if msg.get("_done"):
                # Send final state and close
                final = get_job(job_id)
                await websocket.send_text(json.dumps(final.model_dump(), default=_serialise))
                break

            await websocket.send_text(json.dumps(msg, default=_serialise))
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
