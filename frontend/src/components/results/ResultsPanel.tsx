/**
 * Results panel shown after optimisation completes.
 * Displays:
 *  - KPI cards (before/after pressure drop)
 *  - Optimised geometry parameters
 *  - AI suggestion
 *  - High-loss region annotations
 *  - Download buttons
 */
import { CheckCircle, AlertTriangle, Download, TrendingDown, ArrowRight } from 'lucide-react'
import type { OptimizationResult, JobState } from '../../types'
import { getSTLUrl } from '../../services/api'

interface Props {
  jobId: string
  result: OptimizationResult
  state: JobState
}

function KpiCard({ label, value, unit, highlight }: {
  label: string; value: string; unit: string; highlight?: 'green' | 'red' | 'blue'
}) {
  const colours = {
    green: 'text-green-400 border-green-800 bg-green-900/20',
    red:   'text-red-400   border-red-800   bg-red-900/20',
    blue:  'text-blue-400  border-blue-800  bg-blue-900/20',
  }
  const cls = highlight ? colours[highlight] : 'text-slate-200 border-slate-700 bg-slate-900'
  return (
    <div className={`rounded-xl border p-4 ${cls}`}>
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className="text-2xl font-bold">
        {value} <span className="text-sm font-normal opacity-70">{unit}</span>
      </p>
    </div>
  )
}

export default function ResultsPanel({ jobId, result, state }: Props) {
  const { baseline, optimized, optimized_geometry: optGeom,
          target_achieved, final_pressure_drop_mbar, reduction_pct, suggestion } = result

  return (
    <div className="space-y-5">

      {/* Status banner */}
      <div className={`flex items-center gap-3 rounded-xl p-4 border ${
        target_achieved
          ? 'bg-green-900/20 border-green-800 text-green-300'
          : 'bg-yellow-900/20 border-yellow-800 text-yellow-300'
      }`}>
        {target_achieved
          ? <CheckCircle size={20} />
          : <AlertTriangle size={20} />}
        <div>
          <p className="font-semibold text-sm">
            {target_achieved ? 'Target achieved!' : 'Best result found (target not fully met)'}
          </p>
          <p className="text-xs opacity-80 mt-0.5">
            Pressure drop reduced by {reduction_pct.toFixed(1)}%
          </p>
        </div>
      </div>

      {/* KPI grid */}
      <div className="grid grid-cols-3 gap-3">
        <KpiCard
          label="Baseline ΔP"
          value={baseline.pressure_drop_mbar.toFixed(2)}
          unit="mbar"
          highlight="red"
        />
        <KpiCard
          label="Optimised ΔP"
          value={final_pressure_drop_mbar.toFixed(2)}
          unit="mbar"
          highlight="green"
        />
        <KpiCard
          label="Reduction"
          value={`${reduction_pct.toFixed(1)}%`}
          unit=""
          highlight="blue"
        />
      </div>

      {/* Geometry change */}
      <div className="card">
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-3">
          Geometry Change
        </p>
        <div className="grid grid-cols-2 gap-4 text-sm">
          {[
            ['Bend angle', `${state.result?.baseline ? (state.result.iterations[0]?.bend_angle ?? optGeom.bend_angle) : optGeom.bend_angle}°`, `${optGeom.bend_angle.toFixed(1)}°`],
            ['R/D ratio', '—', `${optGeom.bend_radius_ratio.toFixed(2)}`],
            ['Re baseline', baseline.reynolds_number.toFixed(0), '—'],
            ['K_bend baseline', baseline.bend_loss_coefficient.toFixed(3), optimized.bend_loss_coefficient.toFixed(3)],
          ].map(([label, before, after]) => (
            <div key={label} className="flex items-center gap-2">
              <span className="text-slate-400 text-xs w-28 shrink-0">{label}</span>
              <span className="text-red-400 font-mono text-xs">{before}</span>
              <ArrowRight size={12} className="text-slate-600 shrink-0" />
              <span className="text-green-400 font-mono text-xs">{after}</span>
            </div>
          ))}
        </div>
      </div>

      {/* High-loss regions */}
      {baseline.high_loss_regions.length > 0 && (
        <div className="card">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-3">
            AI Flow Analysis — Loss Regions
          </p>
          <ul className="space-y-2">
            {baseline.high_loss_regions.map((r, i) => (
              <li key={i} className="flex gap-2 text-xs text-slate-300">
                <span className="text-orange-400 mt-0.5 shrink-0">⚠</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Suggestion */}
      <div className="card border-blue-800 bg-blue-900/10">
        <div className="flex gap-2 items-start">
          <TrendingDown size={16} className="text-blue-400 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-medium text-blue-300 uppercase tracking-wide mb-2">
              AI Design Suggestion
            </p>
            <p className="text-xs text-slate-300 leading-relaxed">{suggestion}</p>
          </div>
        </div>
      </div>

      {/* Downloads */}
      <div className="flex gap-3">
        <a href={getSTLUrl(jobId, 'baseline')} download
          className="btn-secondary text-sm flex items-center gap-2 flex-1 justify-center">
          <Download size={14} /> Baseline STL
        </a>
        <a href={getSTLUrl(jobId, 'optimised')} download
          className="btn-primary text-sm flex items-center gap-2 flex-1 justify-center">
          <Download size={14} /> Optimised STL
        </a>
      </div>
    </div>
  )
}
