"""
AeroOpt Platform — FastAPI application entry point.
"""
from __future__ import annotations
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging_setup import setup_logging, logger
from app.api.routes import jobs, geometry


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.debug)
    Path("logs").mkdir(exist_ok=True)
    logger.info(f"AeroOpt Platform v{settings.app_version} starting up.")
    logger.info(f"CFD engine: {settings.cfd_engine}")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-driven aerodynamic optimisation platform. "
        "Upload a pipe geometry, set a pressure-drop target, "
        "and let the system find the optimal shape."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(geometry.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.app_version, "engine": settings.cfd_engine}
