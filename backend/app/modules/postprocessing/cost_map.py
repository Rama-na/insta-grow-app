"""
Post-processing: generate a normalised cost map over the geometry.

The cost map assigns a "loss intensity" score [0, 1] to each axial
section.  This is what the frontend renders as the pressure heatmap.
"""
from __future__ import annotations
import math
from app.models.schemas import CFDResult, SectionResult


def build_cost_map(result: CFDResult) -> list[dict]:
    """
    Returns a list of dicts:
      { "arc_pos": float, "pressure_pa": float, "loss_intensity": float,
        "label": str }

    loss_intensity is in [0, 1], 1 = maximum local loss.
    """
    sections = result.sections
    n = len(sections.arc_positions)
    if n == 0:
        return []

    max_k = max(sections.loss_coefficient) if sections.loss_coefficient else 1.0
    if max_k == 0:
        max_k = 1.0

    cost_map = []
    for i in range(n):
        k = sections.loss_coefficient[i]
        intensity = k / max_k
        s = sections.arc_positions[i]

        if intensity > 0.7:
            label = "high-loss (separation)"
        elif intensity > 0.3:
            label = "moderate loss"
        else:
            label = "low loss"

        cost_map.append({
            "arc_pos": round(s, 4),
            "pressure_pa": round(sections.pressure_pa[i], 2),
            "velocity_ms": round(sections.velocity_ms[i], 3),
            "loss_intensity": round(intensity, 4),
            "label": label,
        })

    return cost_map
