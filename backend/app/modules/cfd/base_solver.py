"""
Abstract base class for all CFD solvers.
New solvers (OpenFOAM, SU2, …) must implement this interface.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from app.models.schemas import (
    BentPipeGeometry, FluidProperties, BoundaryConditions,
    SolverSettings, CFDResult,
)


class BaseCFDSolver(ABC):

    @abstractmethod
    def run(
        self,
        geometry: BentPipeGeometry,
        fluid: FluidProperties,
        boundary: BoundaryConditions,
        solver_settings: SolverSettings,
        job_dir: str | None = None,
    ) -> CFDResult:
        """Execute the simulation and return a structured result."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable solver name."""
