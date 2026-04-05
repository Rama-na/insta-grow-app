import { useState, useRef, useCallback } from 'react'
import type {
  SimulationJobRequest, JobStatus, CFDResult,
  OptimizationIteration, OptimizationResult, WsMessage,
} from '../types'
import { createJob } from '../services/api'

interface OptimizationState {
  jobId: string | null
  status: JobStatus | null
  progress: number
  message: string
  currentIteration: number
  maxIterations: number
  iterations: OptimizationIteration[]
  baseline: CFDResult | null
  baselineLlmAnalysis: string | null
  result: OptimizationResult | null
  error: string | null
  costMap: WsMessage['cost_map']
}

const INITIAL: OptimizationState = {
  jobId: null, status: null, progress: 0, message: '',
  currentIteration: 0, maxIterations: 0, iterations: [],
  baseline: null, baselineLlmAnalysis: null,
  result: null, error: null, costMap: undefined,
}

export function useOptimization() {
  const [state, setState] = useState<OptimizationState>(INITIAL)
  const wsRef = useRef<WebSocket | null>(null)

  const patch = useCallback((updates: Partial<OptimizationState>) => {
    setState(prev => ({ ...prev, ...updates }))
  }, [])

  const submit = useCallback(async (req: SimulationJobRequest) => {
    setState(INITIAL)
    try {
      const res = await createJob(req)
      const jobId = res.data.job_id
      patch({ jobId, status: 'pending', message: 'Job created…' })

      const wsUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/api/jobs/${jobId}/ws`
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onmessage = (ev) => {
        const msg: WsMessage = JSON.parse(ev.data)
        if (msg.heartbeat) return

        setState(prev => {
          const next = { ...prev }
          if (msg.status)            next.status = msg.status
          if (msg.progress_pct != null) next.progress = msg.progress_pct
          if (msg.message)           next.message = msg.message
          if (msg.current_iteration != null) next.currentIteration = msg.current_iteration
          if (msg.baseline)          next.baseline = msg.baseline
          if (msg.baseline_llm_analysis) next.baselineLlmAnalysis = msg.baseline_llm_analysis
          if (msg.cost_map)          next.costMap = msg.cost_map
          if (msg.result)            next.result = msg.result
          if (msg.error)             next.error = msg.error
          if (msg.iteration) {
            next.iterations = [...prev.iterations, msg.iteration]
          }
          return next
        })
      }

      ws.onerror = () => patch({ error: 'WebSocket error. Polling for state…', status: 'failed' })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      patch({ error: msg, status: 'failed' })
    }
  }, [patch])

  const reset = useCallback(() => {
    wsRef.current?.close()
    setState(INITIAL)
  }, [])

  return { state, submit, reset }
}
