# AeroOpt Platform — Running Locally

## Prerequisites
- Python 3.11+ and pip
- Node.js 18+ and npm
- (Optional) Docker + Docker Compose for containerised run

---

## Option A — Direct (no Docker)

### 1. Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:5173

---

## Option B — Docker Compose
```bash
docker compose up --build
```
- App: http://localhost:5173
- API: http://localhost:8000/docs

---

## Demo: 90° Bent Pipe Optimisation

1. Open http://localhost:5173
2. Default settings are pre-loaded:
   - Pipe: D=50mm, bend 90°, R/D=1.5
   - Fluid: Water at 20°C, V=2 m/s
   - Target: reduce ΔP to 2 mbar (from ~10 mbar)
3. Click **Run Optimisation**
4. Watch the convergence chart update in real-time
5. After ~20–25 iterations the optimiser will have found:
   - bend_angle ≈ 25–35°
   - R/D ≈ 3–5
   - ΔP ≈ 1.8–2.2 mbar ✓
6. The results panel shows:
   - Before/after KPIs
   - AI design suggestion (including straight-pipe benchmark)
   - Download links for both STL files

---

## Architecture Summary

```
frontend/ (React + Three.js)
  └── WebSocket → /api/jobs/{id}/ws  (live stream)
  └── POST      → /api/jobs          (create job)
  └── GET       → /api/geometry/centreline

backend/ (FastAPI)
  ├── app/modules/geometry/   ← parametric STL generator
  ├── app/modules/cfd/        ← Analytical + OpenFOAM solvers
  ├── app/modules/optimization/ ← Bayesian optimiser (GP)
  └── app/services/job_service.py ← async job queue
```

## Switching to OpenFOAM

1. Install OpenFOAM 10 on your machine
2. Set `CFD_ENGINE=openfoam` in `backend/.env`
3. Restart the backend

The system automatically falls back to Analytical if OpenFOAM is not found.

---

## Physics Reference (Bent Pipe)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Loss model | Idelchik Table 6-1 | Industry standard for pipe fittings |
| Friction | Colebrook-White | Iterative, valid for all Re |
| K_90 (R/D=1.5) | ≈ 0.40 | High loss |
| K_30 (R/D=3.0) | ≈ 0.06 | Low loss — typical optimum |
| Straight pipe | K = 0 | Friction only → ~0.5 mbar |
