/**
 * Live convergence chart — pressure drop vs iteration number.
 * Shows baseline (dotted) and target (dashed) reference lines.
 */
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Legend,
} from 'recharts'
import type { OptimizationIteration } from '../../types'

interface Props {
  iterations: OptimizationIteration[]
  targetValue: number
  baselineDP: number
}

export default function ConvergenceChart({ iterations, targetValue, baselineDP }: Props) {
  const data = iterations.map(it => ({
    iter: it.iteration,
    dp: parseFloat(it.pressure_drop_mbar.toFixed(3)),
    angle: parseFloat(it.bend_angle.toFixed(1)),
    rd: parseFloat(it.bend_radius_ratio.toFixed(2)),
  }))

  return (
    <div className="w-full">
      <p className="text-xs text-slate-400 mb-3">
        Bayesian optimiser searching for minimum pressure drop near target
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="iter"
            label={{ value: 'Iteration', position: 'insideBottom', offset: -2, fill: '#94a3b8', fontSize: 11 }}
            tick={{ fill: '#64748b', fontSize: 11 }}
          />
          <YAxis
            label={{ value: 'ΔP (mbar)', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 11 }}
            tick={{ fill: '#64748b', fontSize: 11 }}
            domain={['auto', 'auto']}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(val: number, name: string) => {
              if (name === 'dp') return [`${val.toFixed(3)} mbar`, 'ΔP']
              return [val, name]
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />

          <ReferenceLine
            y={baselineDP}
            stroke="#ef4444"
            strokeDasharray="6 4"
            label={{ value: `Baseline ${baselineDP.toFixed(1)} mbar`, fill: '#ef4444', fontSize: 10, position: 'insideTopRight' }}
          />
          <ReferenceLine
            y={targetValue}
            stroke="#22c55e"
            strokeDasharray="6 4"
            label={{ value: `Target ${targetValue} mbar`, fill: '#22c55e', fontSize: 10, position: 'insideBottomRight' }}
          />

          <Line
            type="monotone"
            dataKey="dp"
            name="dp"
            stroke="#60a5fa"
            strokeWidth={2}
            dot={{ fill: '#60a5fa', r: 3 }}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
