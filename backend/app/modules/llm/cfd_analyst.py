"""
LLM-powered CFD analysis using Azure AI Agent (agentaura).

Three entry points:
  analyse_baseline()  — explains what is happening in the initial simulation
  analyse_optimization() — explains what changed and why
  suggest_next_steps() — broader design recommendations
"""
from __future__ import annotations
import math
from app.models.schemas import (
    CFDResult, OptimizationResult,
    BentPipeGeometry, FluidProperties, BoundaryConditions,
)
from app.modules.llm.azure_ai_client import call_agent
from app.core.logging_setup import logger


# ── flow regime helper ────────────────────────────────────────────────────────

def _flow_regime(Re: float) -> str:
    if Re < 2300:
        return "laminar"
    elif Re < 4000:
        return "transitional"
    elif Re < 1e5:
        return "turbulent (moderate Re)"
    else:
        return "fully turbulent"


def _dominant_loss(cfd: CFDResult) -> str:
    """Which loss mechanism dominates — bend or friction?"""
    total = cfd.pressure_drop_mbar
    if total < 1e-9:
        return "negligible"
    K = cfd.bend_loss_coefficient
    dyn_q_mbar = (cfd.inlet_pressure_pa - cfd.outlet_pressure_pa) / 100.0
    if dyn_q_mbar > 0:
        bend_fraction = (K * dyn_q_mbar / total) if total > 0 else 0
        if bend_fraction > 0.6:
            return "bend loss (separation/curvature)"
        elif bend_fraction > 0.3:
            return "mixed (bend + friction)"
    return "wall friction"


# ── baseline analysis ─────────────────────────────────────────────────────────

def analyse_baseline(
    geometry: BentPipeGeometry,
    fluid: FluidProperties,
    boundary: BoundaryConditions,
    result: CFDResult,
) -> str:
    """
    Ask the LLM to explain the baseline CFD result.
    Falls back to rule-based text if LLM is unavailable.
    """
    prompt = f"""You are a senior CFD engineer reviewing a pipe-flow simulation result.
Be concise and technically precise. Use 3-4 sentences maximum.

=== GEOMETRY ===
Pipe type       : {geometry.bend_angle:.1f}° bent pipe
Diameter        : {geometry.diameter * 1000:.1f} mm
Bend R/D ratio  : {geometry.bend_radius_ratio:.1f}
Total length    : {(geometry.inlet_length + geometry.outlet_length):.2f} m (approx, excl. arc)

=== FLOW CONDITIONS ===
Fluid           : density={fluid.density:.1f} kg/m³, viscosity={fluid.dynamic_viscosity:.2e} Pa·s
Inlet velocity  : {boundary.inlet_velocity:.2f} m/s
Reynolds number : {result.reynolds_number:.0f} ({_flow_regime(result.reynolds_number)})

=== SIMULATION RESULTS ===
Total ΔP        : {result.pressure_drop_mbar:.3f} mbar
Bend loss coeff : K = {result.bend_loss_coefficient:.4f}
Friction factor : f = {result.friction_factor:.5f}
Dominant loss   : {_dominant_loss(result)}

High-loss regions identified:
{chr(10).join(f'  • {r}' for r in result.high_loss_regions)}

Task: In 3-4 sentences, explain:
1. What is causing the pressure loss and where it occurs
2. Which region the engineer should focus on to reduce the drop
3. What type of geometry modification would be most effective
"""

    llm_text = call_agent(prompt, max_tokens=350)
    if llm_text:
        return llm_text.strip()

    # ── rule-based fallback ──────────────────────────────────────────────────
    dominant = _dominant_loss(result)
    K = result.bend_loss_coefficient
    regime = _flow_regime(result.reynolds_number)
    lines = [
        f"The {regime} flow (Re={result.reynolds_number:.0f}) through the "
        f"{geometry.bend_angle:.0f}° bend produces a total pressure drop of "
        f"{result.pressure_drop_mbar:.2f} mbar.",

        f"The dominant loss mechanism is {dominant} "
        f"(bend K={K:.3f}, friction f={result.friction_factor:.4f}).",
    ]
    if geometry.bend_angle > 20:
        lines.append(
            f"The outer-bend wall between arc positions "
            f"{geometry.inlet_length/(geometry.inlet_length+geometry.outlet_length):.2f}–"
            f"{1.0:.2f} is the primary high-loss zone due to flow separation and "
            f"centrifugal pressure gradient."
        )
    lines.append(
        f"Recommended action: reduce the bend angle and increase R/D to spread "
        f"the curvature change over a longer arc, suppressing separation."
    )
    return " ".join(lines)


# ── optimisation result analysis ──────────────────────────────────────────────

def analyse_optimization(
    original_geometry: BentPipeGeometry,
    optimized_geometry: BentPipeGeometry,
    result: OptimizationResult,
    target_dp: float,
) -> str:
    """
    Ask the LLM to explain the optimisation outcome.
    Falls back to rule-based text if LLM is unavailable.
    """
    baseline_dp  = result.baseline.pressure_drop_mbar
    final_dp     = result.final_pressure_drop_mbar
    angle_change = original_geometry.bend_angle - optimized_geometry.bend_angle
    rd_change    = optimized_geometry.bend_radius_ratio - original_geometry.bend_radius_ratio

    prompt = f"""You are a senior CFD engineer reviewing the result of an automated
shape optimisation for a bent pipe. Be concise (4-5 sentences max).

=== OPTIMISATION SUMMARY ===
Original geometry : θ={original_geometry.bend_angle:.1f}°, R/D={original_geometry.bend_radius_ratio:.1f}
Optimised geometry: θ={optimized_geometry.bend_angle:.1f}°, R/D={optimized_geometry.bend_radius_ratio:.1f}
Angle reduction   : {angle_change:.1f}°
R/D increase      : +{rd_change:.2f}

Pressure drop:
  Baseline  : {baseline_dp:.3f} mbar
  Optimised : {final_dp:.3f} mbar
  Target    : {target_dp:.3f} mbar
  Reduction : {result.reduction_pct:.1f}%
  Target achieved: {result.target_achieved}

Bend loss coefficient:
  Baseline  : K = {result.baseline.bend_loss_coefficient:.4f}
  Optimised : K = {result.optimized.bend_loss_coefficient:.4f}

Reynolds number: {result.baseline.reynolds_number:.0f}

Task: Explain in 4-5 sentences:
1. Physically why the reduced angle + larger R/D lowered pressure drop
2. Why the target {'was' if result.target_achieved else 'was NOT'} achieved
3. What physical phenomenon sets the lower bound (friction floor)
4. One further design recommendation if more reduction is needed
"""

    llm_text = call_agent(prompt, max_tokens=450)
    if llm_text:
        return llm_text.strip()

    # ── rule-based fallback ──────────────────────────────────────────────────
    lines = []
    if result.target_achieved:
        lines.append(
            f"Target achieved: reducing the bend angle from "
            f"{original_geometry.bend_angle:.0f}° to {optimized_geometry.bend_angle:.1f}° "
            f"and raising R/D from {original_geometry.bend_radius_ratio:.1f} to "
            f"{optimized_geometry.bend_radius_ratio:.1f} cut the pressure drop by "
            f"{result.reduction_pct:.1f}% to {final_dp:.2f} mbar."
        )
    else:
        lines.append(
            f"Best result: {final_dp:.2f} mbar at θ={optimized_geometry.bend_angle:.1f}°, "
            f"R/D={optimized_geometry.bend_radius_ratio:.1f} "
            f"({result.reduction_pct:.1f}% reduction). "
            f"Target of {target_dp:.2f} mbar was not reachable within the given constraints."
        )

    lines.append(
        f"The improvement is driven by lower K (from {result.baseline.bend_loss_coefficient:.3f} "
        f"to {result.optimized.bend_loss_coefficient:.3f}): a shallower, wider bend "
        f"reduces the centrifugal pressure gradient and suppresses boundary-layer separation "
        f"on the outer wall."
    )

    # Compute approximate friction floor
    fric_floor_approx = baseline_dp - (
        result.baseline.bend_loss_coefficient
        * (result.baseline.inlet_pressure_pa - result.baseline.outlet_pressure_pa)
        / 100.0
    )
    if fric_floor_approx > 0:
        lines.append(
            f"The irreducible friction floor for this pipe is approximately "
            f"{fric_floor_approx:.2f} mbar — this cannot be reduced without "
            f"changing pipe diameter or flow velocity."
        )

    return " ".join(lines)


# ── next-steps suggestions ────────────────────────────────────────────────────

def suggest_next_steps(
    result: OptimizationResult,
    target_dp: float,
) -> str:
    """
    After optimisation, ask the LLM for broader design recommendations.
    Returns None if LLM is unavailable (caller handles None).
    """
    prompt = f"""You are a senior fluid-systems engineer advising a design team.
After automated CFD optimisation:

  Baseline ΔP : {result.baseline.pressure_drop_mbar:.2f} mbar (θ={90}°, R/D=1.5)
  Optimised ΔP: {result.final_pressure_drop_mbar:.2f} mbar
  Target ΔP   : {target_dp:.2f} mbar
  Gap remaining: {max(0, result.final_pressure_drop_mbar - target_dp):.2f} mbar

List exactly 3 numbered engineering recommendations that could close any
remaining gap or further improve the design. Each recommendation should be
1-2 sentences. Focus on practical, manufacturing-feasible changes.
"""

    return call_agent(prompt, max_tokens=350)
