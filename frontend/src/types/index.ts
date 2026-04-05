// ── Enums ─────────────────────────────────────────────────────────────────────

export type CFDEngine = 'analytical' | 'openfoam' | 'su2'
export type TurbulenceModel = 'laminar' | 'k_epsilon' | 'k_omega_sst'
export type OptimizationTarget = 'pressure_drop' | 'drag' | 'lift'
export type JobStatus =
  | 'pending' | 'meshing' | 'simulating' | 'optimizing' | 'completed' | 'failed'

// ── Geometry ─────────────────────────────────────────────────────────────────

export interface BentPipeGeometry {
  diameter: number
  wall_thickness: number
  inlet_length: number
  outlet_length: number
  bend_angle: number
  bend_radius_ratio: number
}

// ── Fluid & BCs ───────────────────────────────────────────────────────────────

export interface FluidProperties {
  density: number
  dynamic_viscosity: number
  name: string
}

export interface BoundaryConditions {
  inlet_velocity: number
  outlet_pressure: number
  wall_roughness: number
}

export interface SolverSettings {
  engine: CFDEngine
  turbulence_model: TurbulenceModel
  steady_state: boolean
  max_solver_iterations: number
}

export interface OptimizationConfig {
  target: OptimizationTarget
  target_value: number
  max_iterations: number
  tolerance_pct: number
  bend_angle_min: number
  bend_angle_max: number
  bend_radius_ratio_min: number
  bend_radius_ratio_max: number
}

// ── Job request ───────────────────────────────────────────────────────────────

export interface SimulationJobRequest {
  geometry: BentPipeGeometry
  fluid: FluidProperties
  boundary: BoundaryConditions
  solver: SolverSettings
  optimization: OptimizationConfig
}

// ── CFD results ───────────────────────────────────────────────────────────────

export interface SectionResult {
  arc_positions: number[]
  pressure_pa: number[]
  velocity_ms: number[]
  loss_coefficient: number[]
}

export interface CFDResult {
  pressure_drop_mbar: number
  inlet_pressure_pa: number
  outlet_pressure_pa: number
  reynolds_number: number
  friction_factor: number
  bend_loss_coefficient: number
  sections: SectionResult
  high_loss_regions: string[]
}

export interface OptimizationIteration {
  iteration: number
  bend_angle: number
  bend_radius_ratio: number
  pressure_drop_mbar: number
  improvement_pct: number
  converged: boolean
}

export interface OptimizationResult {
  iterations: OptimizationIteration[]
  baseline: CFDResult
  optimized: CFDResult
  optimized_geometry: BentPipeGeometry
  target_achieved: boolean
  final_pressure_drop_mbar: number
  reduction_pct: number
  suggestion: string
}

// ── Job state ─────────────────────────────────────────────────────────────────

export interface JobState {
  job_id: string
  status: JobStatus
  progress_pct: number
  current_iteration: number
  max_iterations: number
  message: string
  iterations: OptimizationIteration[]
  baseline: CFDResult | null
  result: OptimizationResult | null
  error: string | null
}

// ── WebSocket messages ────────────────────────────────────────────────────────

export interface WsMessage {
  job_id?: string
  status?: JobStatus
  progress_pct?: number
  current_iteration?: number
  message?: string
  iteration?: OptimizationIteration
  baseline?: CFDResult
  cost_map?: Array<{ arc_pos: number; pressure_pa: number; loss_intensity: number; label: string }>
  result?: OptimizationResult
  error?: string
  heartbeat?: boolean
  _done?: boolean
}
