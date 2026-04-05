import axios from 'axios'
import type { SimulationJobRequest, JobState } from '../types'

const api = axios.create({ baseURL: '/api' })

export const createJob = (req: SimulationJobRequest) =>
  api.post<{ job_id: string; status: string; message: string }>('/jobs', req)

export const getJob = (id: string) => api.get<JobState>(`/jobs/${id}`)

export const getSTLUrl = (id: string, variant: 'baseline' | 'optimised') =>
  `/api/jobs/${id}/stl/${variant}`

export const getCentreline = (geom: object) =>
  api.post<{
    points: [number, number, number][]
    arc_positions: number[]
    bend_start_norm: number
    bend_end_norm: number
    total_length_m: number
  }>('/geometry/centreline', geom)
