from app.models.schemas import CFDEngine
from app.modules.cfd.base_solver import BaseCFDSolver
from app.modules.cfd.analytical_solver import AnalyticalSolver
from app.modules.cfd.openfoam_solver import OpenFOAMSolver


def get_solver(engine: CFDEngine) -> BaseCFDSolver:
    match engine:
        case CFDEngine.analytical:
            return AnalyticalSolver()
        case CFDEngine.openfoam:
            return OpenFOAMSolver()
        case CFDEngine.su2:
            # SU2 wrapper would be imported here
            raise NotImplementedError("SU2 solver not yet implemented. Use 'analytical' or 'openfoam'.")
        case _:
            raise ValueError(f"Unknown CFD engine: {engine}")
