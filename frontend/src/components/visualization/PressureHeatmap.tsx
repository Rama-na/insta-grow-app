/**
 * Pressure heatmap — a horizontal bar showing loss intensity
 * along the normalised pipe arc length.
 */
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

interface CostMapEntry {
  arc_pos: number
  pressure_pa: number
  loss_intensity: number
  label: string
}

interface Props {
  costMap: CostMapEntry[]
  bendStart?: number
  bendEnd?: number
  title?: string
}

export default function PressureHeatmap({ costMap, bendStart, bendEnd, title = 'Loss-Intensity Map' }: Props) {
  const data = costMap.map(e => ({
    s: parseFloat(e.arc_pos.toFixed(3)),
    intensity: parseFloat((e.loss_intensity * 100).toFixed(1)),
    pressure: parseFloat((e.pressure_pa / 100).toFixed(2)),
  }))

  return (
    <div>
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-3">{title}</p>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={data} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="lossGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f97316" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#f97316" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="s"
            tick={{ fill: '#64748b', fontSize: 10 }}
            label={{ value: 'Arc position (0→1)', position: 'insideBottom', offset: -2, fill: '#64748b', fontSize: 10 }}
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 10 }}
            label={{ value: 'Loss (%)', angle: -90, position: 'insideLeft', fill: '#64748b', fontSize: 10 }}
            domain={[0, 100]}
          />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            formatter={(v: number, name: string) => {
              if (name === 'intensity') return [`${v.toFixed(1)} %`, 'Loss intensity']
              return [v, name]
            }}
          />
          {bendStart != null && (
            <ReferenceLine x={bendStart} stroke="#fbbf24" strokeDasharray="4 3"
              label={{ value: 'Bend ▶', fill: '#fbbf24', fontSize: 9, position: 'top' }} />
          )}
          {bendEnd != null && (
            <ReferenceLine x={bendEnd} stroke="#fbbf24" strokeDasharray="4 3"
              label={{ value: '◀ End', fill: '#fbbf24', fontSize: 9, position: 'top' }} />
          )}
          <Area type="monotone" dataKey="intensity" stroke="#f97316" fill="url(#lossGrad)"
            strokeWidth={2} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
