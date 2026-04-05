"""
In-process job queue.

Each simulation+optimisation request gets a unique job ID.
Jobs run in a background asyncio task and publish progress
via an asyncio.Queue that the WebSocket endpoint reads.

LLM calls (Azure AI agentaura) happen at two points:
  1. After baseline CFD — to explain the physics of the initial result
  2. After optimisation  — to explain what changed and suggest next steps
Both calls are non-blocking (run_in_executor) and degrade gracefully
when Azure credentials are absent.
"""
from __future__ import annotations
import asyncio
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.logging_setup import logger
from app.models.schemas import (
    SimulationJobRequest, JobState, JobStatus,
    OptimizationIteration, CFDResult,
)
from app.modules.cfd.solver_factory import get_solver
from app.modules.optimization.optimizer import BentPipeOptimizer
from app.modules.postprocessing.cost_map import build_cost_map
from app.modules.llm.cfd_analyst import (
    analyse_baseline, analyse_optimization, suggest_next_steps,
)


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

    loop = asyncio.get_event_loop()

    try:
        # ── Step 1: Meshing ───────────────────────────────────────────────────
        _push({"status": JobStatus.meshing,
               "message": "Generating geometry mesh…", "progress_pct": 5.0})
        await asyncio.sleep(0.1)

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

        # ── Step 2: Baseline CFD ──────────────────────────────────────────────
        _push({"status": JobStatus.simulating,
               "message": "Running baseline CFD simulation…", "progress_pct": 15.0})
        await asyncio.sleep(0.1)

        solver = get_solver(request.solver.engine)
        baseline: CFDResult = await loop.run_in_executor(
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
            "message": f"Baseline CFD complete — ΔP = {baseline.pressure_drop_mbar:.2f} mbar. "
                       f"{'Calling AI for analysis…' if settings.llm_enabled else ''}",
            "progress_pct": 25.0,
            "baseline": baseline,
            "cost_map": cost_map,
        })

        # ── Step 3: LLM baseline analysis (non-blocking) ──────────────────────
        if settings.llm_enabled:
            _push({"message": "AI agent analysing baseline flow field…",
                   "progress_pct": 28.0})
            llm_baseline_analysis = await loop.run_in_executor(
                None,
                lambda: analyse_baseline(
                    request.geometry, request.fluid,
                    request.boundary, baseline
                ),
            )
            state.baseline_llm_analysis = llm_baseline_analysis
            _push({
                "baseline_llm_analysis": llm_baseline_analysis,
                "message": "AI analysis complete. Starting optimisation…",
                "progress_pct": 30.0,
            })
            logger.info(f"[{job_id}] LLM baseline analysis: {llm_baseline_analysis[:80]}…")
        else:
            logger.info(f"[{job_id}] LLM disabled — skipping baseline analysis.")

        # ── Step 4: Bayesian optimisation ─────────────────────────────────────
        _push({"status": JobStatus.optimizing,
               "message": "Starting Bayesian optimisation (Gaussian Process)…",
               "progress_pct": 30.0})

        def _on_iteration(it: OptimizationIteration) -> None:
            state.iterations.append(it)
            progress = 30.0 + (it.iteration / request.optimization.max_iterations) * 60.0
            q.put_nowait({
                "job_id": job_id,
                "status": JobStatus.optimizing,
                "current_iteration": it.iteration,
                "progress_pct": round(progress, 1),
                "iteration": it.model_dump(),
                "message": (
                    f"Iter {it.iteration}/{request.optimization.max_iterations}: "
                    f"θ={it.bend_angle}°  R/D={it.bend_radius_ratio}  "
                    f"ΔP={it.pressure_drop_mbar:.3f} mbar"
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

        opt_result = await loop.run_in_executor(None, optimizer.run)

        # ── Step 5: LLM optimisation analysis ─────────────────────────────────
        if settings.llm_enabled:
            _push({"message": "AI agent reviewing optimisation result…",
                   "progress_pct": 92.0})

            llm_opt_analysis, llm_next_steps = await asyncio.gather(
                loop.run_in_executor(
                    None,
                    lambda: analyse_optimization(
                        request.geometry,
                        opt_result.optimized_geometry,
                        opt_result,
                        request.optimization.target_value,
                    ),
                ),
                loop.run_in_executor(
                    None,
                    lambda: suggest_next_steps(
                        opt_result,
                        request.optimization.target_value,
                    ),
                ),
            )

            opt_result = opt_result.model_copy(update={
                "llm_optimization_analysis": llm_opt_analysis,
                "llm_next_steps": llm_next_steps,
                # Override the rule-based suggestion with LLM analysis
                "suggestion": llm_opt_analysis or opt_result.suggestion,
            })
            logger.info(f"[{job_id}] LLM optimisation analysis complete.")

        # ── Step 6: Generate optimised STL ────────────────────────────────────
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
            "message": (
                f"Complete! ΔP reduced from {baseline.pressure_drop_mbar:.2f} mbar "
                f"to {opt_result.final_pressure_drop_mbar:.2f} mbar "
                f"({opt_result.reduction_pct:.1f}% reduction)"
            ),
            "progress_pct": 100.0,
            "result": opt_result,
        })

    except Exception as exc:
        logger.exception(f"Job {job_id} failed: {exc}")
        _push({
            "status": JobStatus.failed,
            "message": "Job failed — check server logs.",
            "error": str(exc),
        })
    finally:
        q.put_nowait({"job_id": job_id, "_done": True})
