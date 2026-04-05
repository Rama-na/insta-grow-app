/**
 * Full simulation parameter form.
 * Covers geometry, fluid, BCs, solver and optimisation config.
 */
import { useState } from 'react'
import { ChevronDown, ChevronRight, Settings, Waves, Target, Cpu } from 'lucide-react'
import type { SimulationJobRequest } from '../../types'

// ── preset fluids ─────────────────────────────────────────────────────────────

const FLUID_PRESETS = {
  water_20C:   { name: 'water_20C',   density: 998.2,   dynamic_viscosity: 1.002e-3 },
  air_20C:     { name: 'air_20C',     density: 1.204,   dynamic_viscosity: 1.825e-5 },
  glycol_50:   { name: 'glycol_50',   density: 1070.0,  dynamic_viscosity: 4.5e-3   },
}

// ── default values ────────────────────────────────────────────────────────────

const DEFAULT: SimulationJobRequest = {
  geometry: {
    diameter: 0.05,
    wall_thickness: 0.005,
    inlet_length: 0.3,
    outlet_length: 0.3,
    bend_angle: 90,
    bend_radius_ratio: 1.5,
  },
  fluid: FLUID_PRESETS.water_20C,
  boundary: {
    inlet_velocity: 2.0,
    outlet_pressure: 0,
    wall_roughness: 0,
  },
  solver: {
    engine: 'analytical',
    turbulence_model: 'k_omega_sst',
    steady_state: true,
    max_solver_iterations: 500,
  },
  optimization: {
    target: 'pressure_drop',
    target_value: 5.5,   // achievable: friction floor ~4.3 mbar, best bend ~5 mbar
    max_iterations: 25,
    tolerance_pct: 5,
    bend_angle_min: 5,
    bend_angle_max: 90,
    bend_radius_ratio_min: 1.0,
    bend_radius_ratio_max: 8.0,
  },
}

// ── collapsible section ───────────────────────────────────────────────────────

function Section({ title, icon, children, defaultOpen = false }: {
  title: string; icon: React.ReactNode; children: React.ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-slate-800 rounded-xl overflow-hidden mb-3">
      <button
        className="w-full flex items-center gap-2 px-4 py-3 bg-slate-900 hover:bg-slate-800 transition-colors text-left"
        onClick={() => setOpen(o => !o)}
      >
        <span className="text-blue-400">{icon}</span>
        <span className="font-medium text-sm flex-1">{title}</span>
        {open ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
      </button>
      {open && <div className="p-4 bg-slate-950 grid grid-cols-2 gap-3">{children}</div>}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="label">{label}</label>
      {children}
    </div>
  )
}

function NumberInput({ value, onChange, step = 'any', min, max }: {
  value: number; onChange: (v: number) => void; step?: string | number; min?: number; max?: number
}) {
  return (
    <input
      type="number"
      className="input"
      value={value}
      step={step}
      min={min}
      max={max}
      onChange={e => onChange(parseFloat(e.target.value) || 0)}
    />
  )
}

// ── main form ─────────────────────────────────────────────────────────────────

interface Props {
  onSubmit: (req: SimulationJobRequest) => void
  loading?: boolean
}

export default function SimParamsForm({ onSubmit, loading = false }: Props) {
  const [form, setForm] = useState<SimulationJobRequest>(DEFAULT)

  const setGeom = (k: keyof typeof form.geometry, v: number) =>
    setForm(f => ({ ...f, geometry: { ...f.geometry, [k]: v } }))
  const setBound = (k: keyof typeof form.boundary, v: number) =>
    setForm(f => ({ ...f, boundary: { ...f.boundary, [k]: v } }))
  const setOpt = (k: keyof typeof form.optimization, v: number | string) =>
    setForm(f => ({ ...f, optimization: { ...f.optimization, [k]: v } }))

  return (
    <form
      onSubmit={e => { e.preventDefault(); onSubmit(form) }}
      className="space-y-1"
    >
      {/* Geometry */}
      <Section title="Pipe Geometry" icon={<Settings size={15} />} defaultOpen>
        <Field label="Diameter (m)">
          <NumberInput value={form.geometry.diameter} onChange={v => setGeom('diameter', v)} step={0.001} min={0.001} />
        </Field>
        <Field label="Bend Angle (°)">
          <NumberInput value={form.geometry.bend_angle} onChange={v => setGeom('bend_angle', v)} step={1} min={0} max={180} />
        </Field>
        <Field label="R/D ratio">
          <NumberInput value={form.geometry.bend_radius_ratio} onChange={v => setGeom('bend_radius_ratio', v)} step={0.1} min={1} max={20} />
        </Field>
        <Field label="Inlet length (m)">
          <NumberInput value={form.geometry.inlet_length} onChange={v => setGeom('inlet_length', v)} step={0.05} min={0.05} />
        </Field>
        <Field label="Outlet length (m)">
          <NumberInput value={form.geometry.outlet_length} onChange={v => setGeom('outlet_length', v)} step={0.05} min={0.05} />
        </Field>
        <Field label="Wall thickness (m)">
          <NumberInput value={form.geometry.wall_thickness} onChange={v => setGeom('wall_thickness', v)} step={0.001} min={0.001} />
        </Field>
      </Section>

      {/* Fluid */}
      <Section title="Fluid & Flow" icon={<Waves size={15} />} defaultOpen>
        <Field label="Fluid preset">
          <select
            className="input"
            value={form.fluid.name}
            onChange={e => setForm(f => ({ ...f, fluid: FLUID_PRESETS[e.target.value as keyof typeof FLUID_PRESETS] }))}
          >
            <option value="water_20C">Water 20°C</option>
            <option value="air_20C">Air 20°C</option>
            <option value="glycol_50">50% Glycol</option>
          </select>
        </Field>
        <Field label="Inlet velocity (m/s)">
          <NumberInput value={form.boundary.inlet_velocity} onChange={v => setBound('inlet_velocity', v)} step={0.1} min={0.01} />
        </Field>
        <Field label="Density (kg/m³)">
          <input type="number" className="input opacity-60" value={form.fluid.density} readOnly />
        </Field>
        <Field label="Viscosity (Pa·s)">
          <input type="text" className="input opacity-60" value={form.fluid.dynamic_viscosity.toExponential(3)} readOnly />
        </Field>
      </Section>

      {/* Solver */}
      <Section title="Solver" icon={<Cpu size={15} />}>
        <Field label="CFD Engine">
          <select className="input"
            value={form.solver.engine}
            onChange={e => setForm(f => ({ ...f, solver: { ...f.solver, engine: e.target.value as 'analytical' | 'openfoam' } }))}
          >
            <option value="analytical">Analytical (instant)</option>
            <option value="openfoam">OpenFOAM (if installed)</option>
          </select>
        </Field>
        <Field label="Turbulence model">
          <select className="input"
            value={form.solver.turbulence_model}
            onChange={e => setForm(f => ({ ...f, solver: { ...f.solver, turbulence_model: e.target.value as 'k_omega_sst' } }))}
          >
            <option value="laminar">Laminar</option>
            <option value="k_epsilon">k-ε</option>
            <option value="k_omega_sst">k-ω SST</option>
          </select>
        </Field>
      </Section>

      {/* Optimisation */}
      <Section title="Optimisation Target" icon={<Target size={15} />} defaultOpen>
        <Field label="Target ΔP (mbar)">
          <NumberInput value={form.optimization.target_value} onChange={v => setOpt('target_value', v)} step={0.1} min={0.01} />
        </Field>
        <Field label="Max iterations">
          <NumberInput value={form.optimization.max_iterations} onChange={v => setOpt('max_iterations', v)} step={1} min={5} max={100} />
        </Field>
        <Field label="Tolerance (%)">
          <NumberInput value={form.optimization.tolerance_pct} onChange={v => setOpt('tolerance_pct', v)} step={0.5} min={0.5} max={20} />
        </Field>
        <Field label="Min bend angle (°)">
          <NumberInput value={form.optimization.bend_angle_min} onChange={v => setOpt('bend_angle_min', v)} step={1} min={0} />
        </Field>
        <Field label="Max R/D ratio">
          <NumberInput value={form.optimization.bend_radius_ratio_max} onChange={v => setOpt('bend_radius_ratio_max', v)} step={0.5} min={1} />
        </Field>
        <div className="col-span-2 mt-1">
          <p className="text-xs text-slate-500 italic">
            Bayesian optimiser will search the [angle, R/D] space using Gaussian Process surrogate.
          </p>
        </div>
      </Section>

      <button type="submit" disabled={loading} className="btn-primary w-full mt-4 text-sm">
        {loading ? 'Running optimisation…' : 'Run Optimisation'}
      </button>
    </form>
  )
}
