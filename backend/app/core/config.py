from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "AeroOpt Platform"
    app_version: str = "1.0.0"
    debug: bool = False

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    jobs_dir: Path = base_dir / "jobs"
    uploads_dir: Path = base_dir / "uploads"

    # CFD Engine: "analytical" | "openfoam" | "su2"
    cfd_engine: str = "analytical"

    # Optimization defaults
    max_iterations: int = 30
    convergence_tolerance: float = 0.05  # 5% of target

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_file": ".env"}


settings = Settings()

# Ensure runtime dirs exist
settings.jobs_dir.mkdir(parents=True, exist_ok=True)
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
