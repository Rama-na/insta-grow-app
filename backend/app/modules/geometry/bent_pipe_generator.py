"""
Parametric bent-pipe geometry generator.

Produces an STL mesh and a list of cross-section centre-line points that
the post-processor uses to sample CFD scalar fields.

Coordinate convention:
  - Inlet runs along +X
  - Bend sweeps in the XY plane
  - Outlet exits in whatever direction the bend reaches
"""
from __future__ import annotations
import math
from pathlib import Path
from typing import Sequence

import numpy as np

try:
    import trimesh
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False


# ── helpers ──────────────────────────────────────────────────────────────────

def _rotation_matrix_z(angle_rad: float) -> np.ndarray:
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def _circle_points(centre: np.ndarray, normal: np.ndarray,
                   radius: float, n: int = 32) -> np.ndarray:
    """Return *n* evenly-spaced points on a circle."""
    normal = normal / np.linalg.norm(normal)
    # Build an orthonormal basis in the plane
    ref = np.array([0, 0, 1.0]) if abs(normal[2]) < 0.9 else np.array([1, 0, 0.0])
    u = np.cross(normal, ref); u /= np.linalg.norm(u)
    v = np.cross(normal, u)
    angles = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return centre + radius * (np.outer(np.cos(angles), u) +
                              np.outer(np.sin(angles), v))


# ── main generator ────────────────────────────────────────────────────────────

class BentPipeGenerator:
    """
    Generate a hollow bent pipe with:
      - straight inlet section
      - circular-arc bend
      - straight outlet section

    Parameters are intentionally the same as ``BentPipeGeometry`` schema.
    """

    def __init__(
        self,
        diameter: float = 0.05,
        wall_thickness: float = 0.005,
        inlet_length: float = 0.3,
        outlet_length: float = 0.3,
        bend_angle: float = 90.0,
        bend_radius_ratio: float = 1.5,
        radial_segments: int = 32,
        axial_segments_per_diameter: int = 4,
    ):
        self.D = diameter
        self.R_inner = diameter / 2
        self.R_outer = self.R_inner + wall_thickness
        self.L_in = inlet_length
        self.L_out = outlet_length
        self.theta = math.radians(bend_angle)
        self.R_bend = bend_radius_ratio * diameter   # bend centreline radius
        self.n_circ = radial_segments
        self.axial_dpd = axial_segments_per_diameter

    # ── centreline path ───────────────────────────────────────────────────────

    def centreline_points(self, n_sections: int = 50) -> np.ndarray:
        """Return *n_sections* evenly-spaced points along the pipe centreline."""
        arc_len = self.R_bend * self.theta
        total = self.L_in + arc_len + self.L_out

        pts = []
        for i in range(n_sections):
            s = i / (n_sections - 1) * total
            if s <= self.L_in:
                pts.append(np.array([s, 0.0, 0.0]))
            elif s <= self.L_in + arc_len:
                phi = (s - self.L_in) / self.R_bend
                cx = self.L_in + self.R_bend * math.sin(phi)
                cy = self.R_bend - self.R_bend * math.cos(phi)
                pts.append(np.array([cx, cy, 0.0]))
            else:
                t = s - self.L_in - arc_len
                cx = self.L_in + self.R_bend * math.sin(self.theta)
                cy = self.R_bend - self.R_bend * math.cos(self.theta)
                dx = math.cos(self.theta)
                dy = math.sin(self.theta)
                pts.append(np.array([cx + t * dx, cy + t * dy, 0.0]))
        return np.array(pts)

    def arc_lengths_normalised(self, n_sections: int = 50) -> list[float]:
        """Normalised arc length 0→1 for each section."""
        arc_len = self.R_bend * self.theta
        total = self.L_in + arc_len + self.L_out
        return [i / (n_sections - 1) * total / total for i in range(n_sections)]

    # ── STL mesh ──────────────────────────────────────────────────────────────

    def build_stl_mesh(self, path: Path | None = None) -> "trimesh.Trimesh | None":
        """
        Build a surface-mesh STL of the outer pipe wall.
        Returns None (and optionally saves a fallback ASCII STL) when
        trimesh is unavailable.
        """
        if not HAS_TRIMESH:
            if path:
                self._write_ascii_stl(path)
            return None

        sections = self.centreline_points(n_sections=max(20, self.axial_dpd * 10))
        rings = []
        for i, pt in enumerate(sections):
            if i == 0:
                tangent = sections[1] - sections[0]
            elif i == len(sections) - 1:
                tangent = sections[-1] - sections[-2]
            else:
                tangent = sections[i + 1] - sections[i - 1]
            tangent = tangent / np.linalg.norm(tangent)
            rings.append(_circle_points(pt, tangent, self.R_outer, self.n_circ))

        vertices = []
        faces = []
        n = self.n_circ
        for i, ring in enumerate(rings):
            base = len(vertices)
            vertices.extend(ring.tolist())
            if i < len(rings) - 1:
                for j in range(n):
                    a, b = base + j, base + (j + 1) % n
                    c, d = base + n + j, base + n + (j + 1) % n
                    faces.append([a, b, c])
                    faces.append([b, d, c])

        mesh = trimesh.Trimesh(vertices=np.array(vertices),
                               faces=np.array(faces))
        mesh.fix_normals()
        if path:
            mesh.export(str(path))
        return mesh

    def _write_ascii_stl(self, path: Path) -> None:
        """Minimal ASCII STL fallback (just the centreline as a thin strip)."""
        pts = self.centreline_points(20)
        with open(path, "w") as f:
            f.write("solid pipe\n")
            for i in range(len(pts) - 1):
                p0, p1 = pts[i], pts[i + 1]
                f.write("  facet normal 0 0 1\n    outer loop\n")
                for p in (p0, p1, (p0 + p1) / 2):
                    f.write(f"      vertex {p[0]:.6f} {p[1]:.6f} {p[2]:.6f}\n")
                f.write("    endloop\n  endfacet\n")
            f.write("endsolid pipe\n")

    # ── geometry metadata ─────────────────────────────────────────────────────

    def total_length(self) -> float:
        return self.L_in + self.R_bend * self.theta + self.L_out

    def bend_section_fraction(self) -> float:
        return (self.R_bend * self.theta) / self.total_length()

    def bend_start_norm(self) -> float:
        return self.L_in / self.total_length()

    def bend_end_norm(self) -> float:
        return (self.L_in + self.R_bend * self.theta) / self.total_length()
