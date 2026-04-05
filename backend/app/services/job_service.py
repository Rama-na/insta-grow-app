"""
In-process job queue.

Each simulation+optimisation request gets a unique job ID.
Jobs run in a background asyncio task and publish progress
via an asyncio.Queue that the WebSocket endpoint reads.
"""
from __future__ import annotations
import asyncio
import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging_setup import logger
from app.models.schemas import (
    SimulationJobRequest, JobState, JobStatus,
    OptimizationIteration, CFDResult,
)
from app.modules.cfd.solver_factory import get_solver
from app.modules.optimization.optimizer import BentPipeOptimizer
from app.modules.postprocessing.cost_map import build_cost_map


# ── in-memory store ───────────────────────────────────────────────────────────

_jobs: dict[str, JobState] = {}
_queues: dict[str, asyncio.Queue] = {}   # job_id → Queue[dict]


def create_job(request: SimulationJobRequest) -> str:
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = JobState(
        job_id=job_id,
        status=JobStatus.pending,
        max_iterations=request.optimization.max_iterations,
        message="Job created, waiting to start.",
    )
    _queues[job_id] = asyncio.Queue()
    return job_id


def get_job(job_id: str) -> JobState | None:
    return _jobs.get(job_id)


def get_queue(job_id: str) -> asyncio.Queue | None:
    return _queues.get(job_id)


# ── background task ───────────────────────────────────────────────────────────

async def run_job(job_id: str, request: SimulationJobRequest) -> None:
    state = _jobs[job_id]
    q = _queues[job_id]
    job_dir = settings.jobs_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    def _push(update: dict) -> None:
        """Merge update into state and put on queue."""
        for k, v in update.items():
            if hasattr(state, k):
                setattr(state, k, v)
        q.put_nowait({**update, "job_id": job_id})

    try:
        # ── Meshing ──────────────────────────────────────────────────────────
        _push({"status": JobStatus.meshing, "message": "Generating geometry mesh…", "progress_pct": 5.0})
        await asyncio.sleep(0.1)   # yield to event loop

        from app.modules.geometry.bent_pipe_generator import BentPipeGenerator
        gen = BentPipeGenerator(
            diameter=request.geometry.diameter,
            wall_thickness=request.geometry.wall_thickness,
            inlet_length=request.geometry.inlet_length,
            outlet_length=request.geometry.outlet_length,
            bend_angle=request.geometry.bend_angle,
            bend_radius_ratio=request.geometry.bend_radius_ratio,
        )
        gen.build_stl_mesh(job_dir / "baseline.stl")

        # ── Baseline simulation ───────────────────────────────────────────────
        _push({"status": JobStatus.simulating, "message": "Running baseline CFD…", "progress_pct": 15.0})
        await asyncio.sleep(0.1)

        solver = get_solver(request.solver.engine)
        baseline: CFDResult = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: solver.run(
                request.geometry, request.fluid,
                request.boundary, request.solver, str(job_dir)
            ),
        )
        state.baseline = baseline
        cost_map = build_cost_map(baseline)

        _push({
            "status": JobStatus.simulating,
            "message": f"Baseline complete: ΔP = {baseline.pressure_drop_mbar:.2f} mbar",
            "progress_pct": 25.0,
            "baseline": baseline,
            "cost_map": cost_map,
        })

        # ── Optimisation loop ─────────────────────────────────────────────────
        _push({"status": JobStatus.optimizing,
               "message": "Starting optimisation…", "progress_pct": 30.0})

        def _on_iteration(it: OptimizationIteration) -> None:
            state.iterations.append(it)
            progress = 30.0 + (it.iteration / request.optimization.max_iterations) * 65.0
            q.put_nowait({
                "job_id": job_id,
                "status": JobStatus.optimizing,
                "current_iteration": it.iteration,
                "progress_pct": round(progress, 1),
                "iteration": it.model_dump(),
                "message": (
                    f"Iter {it.iteration}: θ={it.bend_angle}°, R/D={it.bend_radius_ratio}, "
                    f"ΔP={it.pressure_drop_mbar:.2f} mbar"
                ),
            })

        optimizer = BentPipeOptimizer(
            geometry=request.geometry,
            fluid=request.fluid,
            boundary=request.boundary,
            solver_settings=request.solver,
            config=request.optimization,
            baseline_result=baseline,
            on_iteration=_on_iteration,
        )

        opt_result = await asyncio.get_event_loop().run_in_executor(None, optimizer.run)

        # Generate optimised geometry STL
        opt_gen = BentPipeGenerator(
            diameter=opt_result.optimized_geometry.diameter,
            wall_thickness=opt_result.optimized_geometry.wall_thickness,
            inlet_length=opt_result.optimized_geometry.inlet_length,
            outlet_length=opt_result.optimized_geometry.outlet_length,
            bend_angle=opt_result.optimized_geometry.bend_angle,
            bend_radius_ratio=opt_result.optimized_geometry.bend_radius_ratio,
        )
        opt_gen.build_stl_mesh(job_dir / "optimised.stl")

        _push({
            "status": JobStatus.completed,
            "message": f"Done! ΔP reduced from {baseline.pressure_drop_mbar:.2f} to {opt_result.final_pressure_drop_mbar:.2f} mbar",
            "progress_pct": 100.0,
            "result": opt_result,
        })

    except Exception as exc:
        logger.exception(f"Job {job_id} failed: {exc}")
        _push({
            "status": JobStatus.failed,
            "message": "Job failed.",
            "error": str(exc),
        })
    finally:
        q.put_nowait({"job_id": job_id, "_done": True})
