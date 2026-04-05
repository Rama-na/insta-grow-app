"""
Geometry endpoints — preview centreline, section data, etc.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.models.schemas import BentPipeGeometry
from app.modules.geometry.bent_pipe_generator import BentPipeGenerator

router = APIRouter(prefix="/api/geometry", tags=["geometry"])


class CentrelineResponse(BaseModel):
    points: list[list[float]]   # [[x, y, z], …]
    arc_positions: list[float]
    bend_start_norm: float
    bend_end_norm: float
    total_length_m: float


@router.post("/centreline", response_model=CentrelineResponse)
def get_centreline(geom: BentPipeGeometry):
    gen = BentPipeGenerator(
        diameter=geom.diameter,
        wall_thickness=geom.wall_thickness,
        inlet_length=geom.inlet_length,
        outlet_length=geom.outlet_length,
        bend_angle=geom.bend_angle,
        bend_radius_ratio=geom.bend_radius_ratio,
    )
    pts = gen.centreline_points(60)
    return CentrelineResponse(
        points=pts.tolist(),
        arc_positions=gen.arc_lengths_normalised(60),
        bend_start_norm=gen.bend_start_norm(),
        bend_end_norm=gen.bend_end_norm(),
        total_length_m=gen.total_length(),
    )
