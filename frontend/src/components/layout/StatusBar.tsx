import type { JobStatus } from '../../types'
import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react'

interface Props {
  status: JobStatus | null
  progress: number
  message: string
  currentIteration: number
  maxIterations: number
}

const STATUS_LABELS: Record<string, string> = {
  pending:    'Queued',
  meshing:    'Meshing',
  simulating: 'Running CFD',
  optimizing: 'Optimising',
  completed:  'Complete',
  failed:     'Failed',
}

export default function StatusBar({ status, progress, message, currentIteration, maxIterations }: Props) {
  if (!status) return null

  const isRunning = status !== 'completed' && status !== 'failed'
  const isFailed  = status === 'failed'

  return (
    <div className="card mb-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {isFailed
            ? <XCircle size={16} className="text-red-400" />
            : status === 'completed'
            ? <CheckCircle size={16} className="text-green-400" />
            : <Loader2 size={16} className="text-blue-400 animate-spin" />}
          <span className={`text-sm font-medium ${isFailed ? 'text-red-400' : status === 'completed' ? 'text-green-400' : 'text-blue-300'}`}>
            {STATUS_LABELS[status] ?? status}
          </span>
          {status === 'optimizing' && maxIterations > 0 && (
            <span className="text-xs text-slate-500">
              ({currentIteration}/{maxIterations})
            </span>
          )}
        </div>
        <span className="text-xs text-slate-500">{progress.toFixed(0)}%</span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden mb-2">
        <div
          className={`h-full rounded-full transition-all duration-300 ${
            isFailed ? 'bg-red-500' : status === 'completed' ? 'bg-green-500' : 'bg-blue-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>

      <p className="text-xs text-slate-400 truncate">{message}</p>
    </div>
  )
}
