"""
Bayesian Optimization engine for aerodynamic shape optimization.

Design variables (for bent-pipe):
  x[0] = bend_angle      (degrees)
  x[1] = bend_radius_ratio (R/D)

Objective: minimise |ΔP - target_ΔP|

Uses scikit-optimize's Gaussian-process-based Bayesian optimizer.
Falls back to a dense grid search if scikit-optimize is unavailable.
"""
from __future__ import annotations
import asyncio
import math
from typing import AsyncIterator, Callable

from app.models.schemas import (
    BentPipeGeometry, FluidProperties, BoundaryConditions,
    SolverSettings, OptimizationConfig, OptimizationIteration,
    OptimizationResult, CFDResult,
)
from app.modules.cfd.solver_factory import get_solver
from app.core.logging_setup import logger

try:
    from skopt import gp_minimize
    from skopt.space import Real
    HAS_SKOPT = True
except ImportError:
    HAS_SKOPT = False


# ── optimizer ─────────────────────────────────────────────────────────────────

class BentPipeOptimizer:
    """
    Iteratively adjust bend_angle and bend_radius_ratio to reach the
    target pressure drop.

    Emits ``OptimizationIteration`` objects via an async generator so
    the API layer can stream progress over WebSocket.
    """

    def __init__(
        self,
        geometry: BentPipeGeometry,
        fluid: FluidProperties,
        boundary: BoundaryConditions,
        solver_settings: SolverSettings,
        config: OptimizationConfig,
        baseline_result: CFDResult,
        on_iteration: Callable[[OptimizationIteration], None] | None = None,
    ):
        self.base_geometry = geometry
        self.fluid = fluid
        self.boundary = boundary
        self.solver_settings = solver_settings
        self.config = config
        self.baseline = baseline_result
        self.on_iteration = on_iteration
        self._iterations: list[OptimizationIteration] = []
        self._eval_count = 0

    # ── objective function ────────────────────────────────────────────────────

    def _evaluate(self, params: list[float]) -> float:
        angle, r_d = params
        geom = self.base_geometry.model_copy(update={
            "bend_angle": float(angle),
            "bend_radius_ratio": float(r_d),
        })
        solver = get_solver(self.solver_settings.engine)
        result = solver.run(geom, self.fluid, self.boundary, self.solver_settings)

        target = self.config.target_value
        dp = result.pressure_drop_mbar
        error = abs(dp - target)

        self._eval_count += 1
        improvement = (self.baseline.pressure_drop_mbar - dp) / self.baseline.pressure_drop_mbar * 100
        tol_abs = target * self.config.tolerance_pct / 100.0
        converged = dp <= target + tol_abs and dp >= max(0, target - tol_abs)

        iter_obj = OptimizationIteration(
            iteration=self._eval_count,
            bend_angle=round(angle, 2),
            bend_radius_ratio=round(r_d, 3),
            pressure_drop_mbar=round(dp, 4),
            improvement_pct=round(improvement, 2),
            converged=converged,
        )
        self._iterations.append(iter_obj)
        if self.on_iteration:
            self.on_iteration(iter_obj)

        logger.debug(
            f"[iter {self._eval_count:02d}] θ={angle:.1f}° R/D={r_d:.2f} "
            f"→ ΔP={dp:.3f} mbar  error={error:.4f}"
        )
        return error

    # ── straight-pipe suggestion ──────────────────────────────────────────────

    def _straight_pipe_pressure_drop(self) -> float:
        geom = self.base_geometry.model_copy(update={"bend_angle": 0.0})
        solver = get_solver(self.solver_settings.engine)
        r = solver.run(geom, self.fluid, self.boundary, self.solver_settings)
        return r.pressure_drop_mbar

    # ── main optimize method ──────────────────────────────────────────────────

    def run(self) -> OptimizationResult:
        cfg = self.config
        spaces = [
            (cfg.bend_angle_min, cfg.bend_angle_max),
            (cfg.bend_radius_ratio_min, cfg.bend_radius_ratio_max),
        ]

        best_params: list[float] = [
            self.base_geometry.bend_angle,
            self.base_geometry.bend_radius_ratio,
        ]

        if HAS_SKOPT:
            logger.info("Starting Bayesian optimisation (GP-minimise)")
            sk_spaces = [Real(*s) for s in spaces]
            res = gp_minimize(
                self._evaluate,
                sk_spaces,
                n_calls=cfg.max_iterations,
                n_initial_points=min(8, cfg.max_iterations // 3),
                acq_func="EI",
                noise=1e-10,
                random_state=42,
            )
            best_params = list(res.x)
        else:
            logger.warning("scikit-optimize not available — using adaptive grid search.")
            best_params = self._grid_search(spaces, cfg.max_iterations)

        # Final evaluation at best point
        best_angle, best_r_d = best_params
        best_geom = self.base_geometry.model_copy(update={
            "bend_angle": round(best_angle, 2),
            "bend_radius_ratio": round(best_r_d, 3),
        })
        solver = get_solver(self.solver_settings.engine)
        optimized_result = solver.run(best_geom, self.fluid, self.boundary, self.solver_settings)

        final_dp = optimized_result.pressure_drop_mbar
        tol_abs = cfg.target_value * cfg.tolerance_pct / 100.0
        target_achieved = abs(final_dp - cfg.target_value) <= tol_abs or final_dp <= cfg.target_value

        reduction_pct = (
            (self.baseline.pressure_drop_mbar - final_dp)
            / self.baseline.pressure_drop_mbar * 100
        )

        straight_dp = self._straight_pipe_pressure_drop()
        suggestion = self._build_suggestion(
            best_angle, best_r_d, final_dp, straight_dp, target_achieved
        )

        return OptimizationResult(
            iterations=self._iterations,
            baseline=self.baseline,
            optimized=optimized_result,
            optimized_geometry=best_geom,
            target_achieved=target_achieved,
            final_pressure_drop_mbar=round(final_dp, 4),
            reduction_pct=round(reduction_pct, 2),
            suggestion=suggestion,
        )

    # ── fallback grid search ──────────────────────────────────────────────────

    def _grid_search(self, spaces: list[tuple], n_calls: int) -> list[float]:
        n_side = max(4, int(math.sqrt(n_calls)))
        angles = [
            spaces[0][0] + i / (n_side - 1) * (spaces[0][1] - spaces[0][0])
            for i in range(n_side)
        ]
        r_ds = [
            spaces[1][0] + i / (n_side - 1) * (spaces[1][1] - spaces[1][0])
            for i in range(n_side)
        ]
        best_err = float("inf")
        best = [spaces[0][0], spaces[1][0]]
        for a in angles:
            for r in r_ds:
                if self._eval_count >= n_calls:
                    break
                err = self._evaluate([a, r])
                if err < best_err:
                    best_err = err
                    best = [a, r]
        return best

    # ── suggestion text ───────────────────────────────────────────────────────

    def _build_suggestion(
        self,
        angle: float,
        r_d: float,
        dp: float,
        straight_dp: float,
        achieved: bool,
    ) -> str:
        lines = []
        if achieved:
            lines.append(
                f"Target achieved: reducing bend angle to {angle:.1f}° "
                f"with R/D={r_d:.1f} reduces pressure drop to {dp:.2f} mbar."
            )
        else:
            lines.append(
                f"Best result found: {dp:.2f} mbar at θ={angle:.1f}°, R/D={r_d:.1f}. "
                f"Target of {self.config.target_value} mbar could not be reached "
                f"within the given geometric constraints."
            )

        lines.append(
            f"Design insight: the dominant loss is at the outer-bend wall due to "
            f"flow separation. Increasing the bend radius ratio (R/D) spreads the "
            f"pressure gradient over a longer arc, reducing peak losses."
        )

        lines.append(
            f"Maximum possible reduction: a straight pipe (θ=0°) would yield "
            f"approximately {straight_dp:.2f} mbar — pure friction loss only."
        )

        if straight_dp <= self.config.target_value:
            lines.append(
                f"Note: a straight-pipe layout would comfortably meet your target. "
                f"Consider routing changes if the design envelope allows."
            )

        return " ".join(lines)
