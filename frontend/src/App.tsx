/**
 * AeroOpt Platform — main application shell.
 *
 * Layout:
 *  Left panel  (40%) → input form + status bar + results summary
 *  Right panel (60%) → 3-D viewer + convergence chart + heatmap
 */
import { useState, useEffect } from 'react'
import { Wind, RotateCcw, Github } from 'lucide-react'
import SimParamsForm from './components/params/SimParamsForm'
import PipeViewer3D from './components/visualization/PipeViewer3D'
import ConvergenceChart from './components/visualization/ConvergenceChart'
import PressureHeatmap from './components/visualization/PressureHeatmap'
import ResultsPanel from './components/results/ResultsPanel'
import AIInsightPanel from './components/results/AIInsightPanel'
import StatusBar from './components/layout/StatusBar'
import { useOptimization } from './hooks/useOptimization'
import { getCentreline } from './services/api'
import type { SimulationJobRequest, BentPipeGeometry } from './types'

type CentrelineData = {
  points: [number, number, number][]
  arc_positions: number[]
  bend_start_norm: number
  bend_end_norm: number
}

export default function App() {
  const { state, submit, reset } = useOptimization()
  const [baselineCL, setBaselineCL] = useState<CentrelineData | null>(null)
  const [optimisedCL, setOptimisedCL] = useState<CentrelineData | null>(null)
  const [currentGeom, setCurrentGeom] = useState<BentPipeGeometry | null>(null)
  const [activeTab, setActiveTab] = useState<'3d' | 'convergence' | 'heatmap'>('3d')
  const [targetValue, setTargetValue] = useState(5.5)

  // Fetch centrepoints when baseline arrives
  useEffect(() => {
    if (state.baseline && currentGeom && !baselineCL) {
      getCentreline(currentGeom)
        .then(r => setBaselineCL(r.data))
        .catch(console.error)
    }
  }, [state.baseline, currentGeom, baselineCL])

  // Fetch optimised centreline when result arrives
  useEffect(() => {
    if (state.result?.optimized_geometry && !optimisedCL) {
      getCentreline(state.result.optimized_geometry)
        .then(r => setOptimisedCL(r.data))
        .catch(console.error)
    }
  }, [state.result, optimisedCL])

  const handleSubmit = (req: SimulationJobRequest) => {
    setBaselineCL(null)
    setOptimisedCL(null)
    setCurrentGeom(req.geometry)
    setTargetValue(req.optimization.target_value)
    submit(req)
  }

  const handleReset = () => {
    reset()
    setBaselineCL(null)
    setOptimisedCL(null)
    setCurrentGeom(null)
    setActiveTab('3d')
  }

  const isRunning = state.status !== null && state.status !== 'completed' && state.status !== 'failed'
  const isDone    = state.status === 'completed'

  return (
    <div className="min-h-screen flex flex-col">

      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-3 flex items-center justify-between bg-slate-950">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 rounded-lg p-1.5">
            <Wind size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-tight">AeroOpt Platform</h1>
            <p className="text-xs text-slate-500">AI-driven aerodynamic optimisation</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {state.status && (
            <button onClick={handleReset} className="btn-secondary text-xs flex items-center gap-1.5">
              <RotateCcw size={12} /> New run
            </button>
          )}
          <span className="text-xs text-slate-600">Powered by CFD + Bayesian Opt</span>
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">

        {/* ── Left panel ─────────────────────────────────────────────────── */}
        <aside className="w-96 shrink-0 border-r border-slate-800 overflow-y-auto p-4 bg-slate-950">

          {/* Status bar (visible while running) */}
          <StatusBar
            status={state.status}
            progress={state.progress}
            message={state.message}
            currentIteration={state.currentIteration}
            maxIterations={state.maxIterations}
          />

          {/* Show form when idle */}
          {!state.status && (
            <>
              <div className="mb-4">
                <h2 className="text-sm font-semibold text-slate-200 mb-1">90° Bent Pipe Example</h2>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Configure a 90° pipe bend and set a target pressure drop.
                  The Bayesian optimiser will find the optimal bend angle and
                  R/D ratio to meet your target.
                </p>
              </div>
              <SimParamsForm onSubmit={handleSubmit} loading={isRunning} />
            </>
          )}

          {/* AI baseline analysis — shown as soon as available (even mid-run) */}
          {state.baselineLlmAnalysis && !isDone && (
            <div className="mt-4">
              <AIInsightPanel baselineAnalysis={state.baselineLlmAnalysis} />
            </div>
          )}

          {/* Show results when done */}
          {isDone && state.result && state.jobId && (
            <ResultsPanel
              jobId={state.jobId}
              result={state.result}
              state={state}
              baselineLlmAnalysis={state.baselineLlmAnalysis}
            />
          )}

          {/* Error state */}
          {state.status === 'failed' && state.error && (
            <div className="card border-red-800 bg-red-900/10 text-red-300 text-xs">
              <p className="font-medium mb-1">Error</p>
              <p>{state.error}</p>
            </div>
          )}

          {/* Show condensed form while running */}
          {isRunning && (
            <div className="mt-4 card">
              <p className="text-xs text-slate-400 italic">
                Optimisation running… results will appear in the right panel in real-time.
              </p>
            </div>
          )}
        </aside>

        {/* ── Right panel ────────────────────────────────────────────────── */}
        <main className="flex-1 flex flex-col overflow-hidden">

          {/* Tab bar */}
          <div className="border-b border-slate-800 px-4 flex gap-1 pt-3 bg-slate-950">
            {(['3d', 'convergence', 'heatmap'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-2 text-xs font-medium rounded-t-lg border-b-2 transition-colors ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-400 bg-slate-900'
                    : 'border-transparent text-slate-500 hover:text-slate-300'
                }`}
              >
                {tab === '3d' ? '3D Viewer' : tab === 'convergence' ? 'Convergence' : 'Loss Map'}
              </button>
            ))}

            {/* Iteration badges */}
            {state.iterations.length > 0 && (
              <div className="ml-auto flex items-center gap-2 pb-2">
                <span className="badge-blue">
                  {state.iterations.length} evals
                </span>
                {state.iterations.length > 0 && (
                  <span className="badge-green">
                    Best: {Math.min(...state.iterations.map(i => i.pressure_drop_mbar)).toFixed(2)} mbar
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-auto p-4">

            {activeTab === '3d' && (
              <div className="h-full min-h-[400px]">
                <PipeViewer3D
                  baselineResult={state.baseline ?? undefined}
                  optimizedResult={state.result?.optimized ?? undefined}
                  baselinePoints={baselineCL?.points}
                  optimizedPoints={optimisedCL?.points}
                  geometry={currentGeom ?? undefined}
                  showBoth={!!state.result}
                />
                {baselineCL && (
                  <div className="mt-3 flex gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1.5">
                      <span className="inline-block w-3 h-1 rounded bg-blue-500 opacity-50" />
                      Baseline (semi-transparent)
                    </span>
                    {optimisedCL && (
                      <span className="flex items-center gap-1.5">
                        <span className="inline-block w-3 h-1 rounded bg-blue-500" />
                        Optimised geometry
                      </span>
                    )}
                    <span className="ml-auto italic">Colour = static pressure (blue→low, red→high)</span>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'convergence' && (
              <div className="card h-full">
                <h3 className="text-sm font-medium text-slate-200 mb-1">Optimisation Convergence</h3>
                {state.iterations.length === 0 ? (
                  <p className="text-xs text-slate-500 italic mt-8 text-center">
                    Start optimisation to see convergence data.
                  </p>
                ) : (
                  <ConvergenceChart
                    iterations={state.iterations}
                    targetValue={targetValue}
                    baselineDP={state.baseline?.pressure_drop_mbar ?? 11}
                  />
                )}

                {/* Iteration table */}
                {state.iterations.length > 0 && (
                  <div className="mt-4 overflow-auto max-h-48">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-slate-500 border-b border-slate-800">
                          <th className="text-left py-1 pr-3">#</th>
                          <th className="text-right pr-3">θ (°)</th>
                          <th className="text-right pr-3">R/D</th>
                          <th className="text-right pr-3">ΔP (mbar)</th>
                          <th className="text-right">Δ%</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...state.iterations].reverse().slice(0, 20).map(it => (
                          <tr key={it.iteration} className={`border-b border-slate-900 ${it.converged ? 'text-green-400' : 'text-slate-300'}`}>
                            <td className="py-1 pr-3 text-slate-500">{it.iteration}</td>
                            <td className="text-right pr-3 font-mono">{it.bend_angle.toFixed(1)}</td>
                            <td className="text-right pr-3 font-mono">{it.bend_radius_ratio.toFixed(2)}</td>
                            <td className="text-right pr-3 font-mono">{it.pressure_drop_mbar.toFixed(3)}</td>
                            <td className="text-right font-mono">{it.improvement_pct.toFixed(1)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'heatmap' && (
              <div className="card h-full space-y-6">
                <h3 className="text-sm font-medium text-slate-200">Pressure Loss Map Along Pipe</h3>
                {!state.costMap ? (
                  <p className="text-xs text-slate-500 italic text-center mt-8">
                    Run simulation to see the loss map.
                  </p>
                ) : (
                  <>
                    <PressureHeatmap
                      costMap={state.costMap}
                      bendStart={baselineCL?.bend_start_norm}
                      bendEnd={baselineCL?.bend_end_norm}
                      title="Baseline — Loss Intensity"
                    />
                    {state.result && state.costMap && (
                      <div className="text-xs text-slate-400 italic">
                        Peak loss region: outer-bend wall between the bend start and end markers.
                        The optimiser reduces this by spreading the curvature change over a longer arc.
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
