"""
Pydantic schemas for the AeroOpt API.
All pressure values are in mbar, lengths in meters, angles in degrees.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ── Enums ────────────────────────────────────────────────────────────────────

class CFDEngine(str, Enum):
    analytical = "analytical"
    openfoam = "openfoam"
    su2 = "su2"


class TurbulenceModel(str, Enum):
    laminar = "laminar"
    k_epsilon = "k_epsilon"
    k_omega_sst = "k_omega_sst"


class OptimizationTarget(str, Enum):
    pressure_drop = "pressure_drop"
    drag = "drag"
    lift = "lift"


class JobStatus(str, Enum):
    pending = "pending"
    meshing = "meshing"
    simulating = "simulating"
    optimizing = "optimizing"
    completed = "completed"
    failed = "failed"


# ── Geometry ─────────────────────────────────────────────────────────────────

class BentPipeGeometry(BaseModel):
    diameter: float = Field(0.05, gt=0, description="Pipe inner diameter (m)")
    wall_thickness: float = Field(0.005, gt=0, description="Pipe wall thickness (m)")
    inlet_length: float = Field(0.3, gt=0, description="Straight inlet section (m)")
    outlet_length: float = Field(0.3, gt=0, description="Straight outlet section (m)")
    bend_angle: float = Field(90.0, ge=0, le=180, description="Bend angle (degrees)")
    bend_radius_ratio: float = Field(1.5, ge=1.0, le=10.0, description="R/D ratio")


# ── Fluid & Boundary Conditions ───────────────────────────────────────────────

class FluidProperties(BaseModel):
    density: float = Field(998.2, gt=0, description="Fluid density (kg/m³) — default: water at 20°C")
    dynamic_viscosity: float = Field(1.002e-3, gt=0, description="Dynamic viscosity (Pa·s)")
    name: str = Field("water_20C", description="Fluid preset label")


class BoundaryConditions(BaseModel):
    inlet_velocity: float = Field(2.0, gt=0, description="Inlet velocity (m/s)")
    outlet_pressure: float = Field(0.0, description="Outlet gauge pressure (Pa)")
    wall_roughness: float = Field(0.0, ge=0, description="Wall roughness height (m), 0 = smooth")


class SolverSettings(BaseModel):
    engine: CFDEngine = CFDEngine.analytical
    turbulence_model: TurbulenceModel = TurbulenceModel.k_omega_sst
    steady_state: bool = True
    max_solver_iterations: int = Field(500, gt=0)


# ── Optimization ──────────────────────────────────────────────────────────────

class OptimizationConfig(BaseModel):
    target: OptimizationTarget = OptimizationTarget.pressure_drop
    target_value: float = Field(..., description="Desired target value (mbar for pressure drop)")
    max_iterations: int = Field(25, ge=1, le=100)
    tolerance_pct: float = Field(5.0, ge=0.1, le=20.0, description="Convergence tolerance (%)")
    # Bounds for optimization variables
    bend_angle_min: float = Field(5.0, ge=0)
    bend_angle_max: float = Field(90.0, le=180)
    bend_radius_ratio_min: float = Field(1.0, ge=0.5)
    bend_radius_ratio_max: float = Field(8.0, le=20.0)


# ── Job ───────────────────────────────────────────────────────────────────────

class SimulationJobRequest(BaseModel):
    geometry: BentPipeGeometry = BentPipeGeometry()
    fluid: FluidProperties = FluidProperties()
    boundary: BoundaryConditions = BoundaryConditions()
    solver: SolverSettings = SolverSettings()
    optimization: OptimizationConfig


class JobCreatedResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str


# ── CFD Results ───────────────────────────────────────────────────────────────

class SectionResult(BaseModel):
    """Scalar fields sampled at N cross-sections along the pipe centre-line."""
    arc_positions: list[float]         # normalised arc length 0→1
    pressure_pa: list[float]           # static pressure (Pa)
    velocity_ms: list[float]           # centreline velocity (m/s)
    loss_coefficient: list[float]      # local K distribution


class CFDResult(BaseModel):
    pressure_drop_mbar: float
    inlet_pressure_pa: float
    outlet_pressure_pa: float
    reynolds_number: float
    friction_factor: float
    bend_loss_coefficient: float
    sections: SectionResult
    high_loss_regions: list[str]       # text annotations ("outer bend wall", …)


# ── Optimisation iteration ─────────────────────────────────────────────────

class OptimizationIteration(BaseModel):
    iteration: int
    bend_angle: float
    bend_radius_ratio: float
    pressure_drop_mbar: float
    improvement_pct: float
    converged: bool


class OptimizationResult(BaseModel):
    iterations: list[OptimizationIteration]
    baseline: CFDResult
    optimized: CFDResult
    optimized_geometry: BentPipeGeometry
    target_achieved: bool
    final_pressure_drop_mbar: float
    reduction_pct: float
    suggestion: str


# ── Job state returned by /jobs/{id} ─────────────────────────────────────────

class JobState(BaseModel):
    job_id: str
    status: JobStatus
    progress_pct: float = 0.0
    current_iteration: int = 0
    max_iterations: int = 0
    message: str = ""
    iterations: list[OptimizationIteration] = []
    baseline: Optional[CFDResult] = None
    result: Optional[OptimizationResult] = None
    error: Optional[str] = None
