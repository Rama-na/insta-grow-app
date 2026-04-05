"""
OpenFOAM solver wrapper.

This module is a structured stub ready for real OpenFOAM integration.
It validates the environment, generates the case directory, and would
invoke `blockMesh`, `snappyHexMesh`, and `simpleFoam`/`pimpleFoam`.

To activate: install OpenFOAM 10+ and set CFD_ENGINE=openfoam in .env
"""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path

from app.models.schemas import (
    BentPipeGeometry, FluidProperties, BoundaryConditions,
    SolverSettings, CFDResult,
)
from app.modules.cfd.base_solver import BaseCFDSolver
from app.modules.cfd.analytical_solver import AnalyticalSolver
from app.core.logging_setup import logger


OPENFOAM_AVAILABLE = shutil.which("simpleFoam") is not None


class OpenFOAMSolver(BaseCFDSolver):
    """
    Wraps OpenFOAM simpleFoam for steady RANS pipe-bend simulation.
    Falls back to AnalyticalSolver when OpenFOAM is not installed.
    """

    @property
    def name(self) -> str:
        return "OpenFOAM (simpleFoam + k-ω SST)" if OPENFOAM_AVAILABLE else "OpenFOAM [fallback→Analytical]"

    def run(
        self,
        geometry: BentPipeGeometry,
        fluid: FluidProperties,
        boundary: BoundaryConditions,
        solver_settings: SolverSettings,
        job_dir: str | None = None,
    ) -> CFDResult:

        if not OPENFOAM_AVAILABLE:
            logger.warning("OpenFOAM not found — falling back to analytical solver.")
            return AnalyticalSolver().run(geometry, fluid, boundary, solver_settings, job_dir)

        case_dir = Path(job_dir) / "openfoam_case" if job_dir else Path("/tmp/of_case")
        case_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._write_case(case_dir, geometry, fluid, boundary, solver_settings)
            self._run_mesher(case_dir)
            self._run_solver(case_dir)
            return self._parse_results(case_dir, geometry, fluid, boundary)
        except Exception as exc:
            logger.error(f"OpenFOAM run failed: {exc}. Falling back to analytical.")
            return AnalyticalSolver().run(geometry, fluid, boundary, solver_settings, job_dir)

    # ── case generation ───────────────────────────────────────────────────────

    def _write_case(self, case_dir: Path, geom, fluid, bc, solver) -> None:
        """Write all OpenFOAM dict files."""
        (case_dir / "system").mkdir(exist_ok=True)
        (case_dir / "constant").mkdir(exist_ok=True)
        (case_dir / "0").mkdir(exist_ok=True)

        # controlDict
        (case_dir / "system" / "controlDict").write_text(f"""\
FoamFile {{ version 2.0; format ascii; class dictionary; location "system"; object controlDict; }}
application     simpleFoam;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         {solver.max_solver_iterations};
deltaT          1;
writeControl    timeStep;
writeInterval   100;
purgeWrite      2;
writeFormat     ascii;
writePrecision  6;
runTimeModifiable yes;
functions
{{
    pressureDrop
    {{
        type            fieldValueDelta;
        libs            ("libfieldFunctionObjects.so");
        region1         {{ regionType patch; name inlet; }}
        region2         {{ regionType patch; name outlet; }}
        fields          (p);
        writeToFile     yes;
    }}
}}
""")

        # fvSchemes
        (case_dir / "system" / "fvSchemes").write_text("""\
FoamFile { version 2.0; format ascii; class dictionary; object fvSchemes; }
ddtSchemes   { default steadyState; }
gradSchemes  { default Gauss linear; }
divSchemes   { default none; div(phi,U) bounded Gauss linearUpwind grad(U); div(phi,k) bounded Gauss upwind; div(phi,omega) bounded Gauss upwind; div((nuEff*dev(T(grad(U))))) Gauss linear; }
laplacianSchemes { default Gauss linear corrected; }
interpolationSchemes { default linear; }
snGradSchemes { default corrected; }
""")

        # fvSolution
        (case_dir / "system" / "fvSolution").write_text("""\
FoamFile { version 2.0; format ascii; class dictionary; object fvSolution; }
solvers { p { solver GAMG; tolerance 1e-7; relTol 0.01; smoother GaussSeidel; } U { solver smoothSolver; smoother GaussSeidel; tolerance 1e-8; relTol 0.1; } k { solver smoothSolver; smoother GaussSeidel; tolerance 1e-8; relTol 0.1; } omega { solver smoothSolver; smoother GaussSeidel; tolerance 1e-8; relTol 0.1; } }
SIMPLE { nNonOrthogonalCorrectors 2; residualControl { p 1e-4; U 1e-4; } }
relaxationFactors { fields { p 0.3; } equations { U 0.7; k 0.5; omega 0.5; } }
""")

        # transportProperties
        nu = fluid.dynamic_viscosity / fluid.density
        (case_dir / "constant" / "transportProperties").write_text(f"""\
FoamFile {{ version 2.0; format ascii; class dictionary; object transportProperties; }}
transportModel  Newtonian;
nu              {nu:.6e};
""")

        # turbulenceProperties
        (case_dir / "constant" / "turbulenceProperties").write_text("""\
FoamFile { version 2.0; format ascii; class dictionary; object turbulenceProperties; }
simulationType  RAS;
RAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }
""")

        logger.debug(f"OpenFOAM case written to {case_dir}")

    def _run_mesher(self, case_dir: Path) -> None:
        subprocess.run(["blockMesh"], cwd=case_dir, check=True,
                       capture_output=True, timeout=300)
        logger.info("blockMesh completed.")

    def _run_solver(self, case_dir: Path) -> None:
        subprocess.run(["simpleFoam"], cwd=case_dir, check=True,
                       capture_output=True, timeout=1800)
        logger.info("simpleFoam completed.")

    def _parse_results(self, case_dir: Path, geom, fluid, bc) -> CFDResult:
        """Parse postProcessing/pressureDrop for ΔP and delegate field data."""
        pp_path = case_dir / "postProcessing" / "pressureDrop"
        dP_pa = 0.0
        if pp_path.exists():
            for f in sorted(pp_path.iterdir()):
                lines = (f / "fieldValueDelta.dat").read_text().splitlines()
                for line in reversed(lines):
                    if not line.startswith("#"):
                        dP_pa = abs(float(line.split()[-1])) * fluid.density
                        break
                break

        # Reuse analytical solver for section-level data
        from app.models.schemas import SolverSettings
        analytical = AnalyticalSolver().run(geom, fluid, bc, SolverSettings())
        return analytical.model_copy(update={"pressure_drop_mbar": dP_pa / 100.0})
