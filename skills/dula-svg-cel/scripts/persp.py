#!/usr/bin/env python3
"""Perspective for SVG plates: `Camera` (a real pinhole projection for whole rooms, preferred) and
`Wall` (a one-plane approximation).

Wall-plane perspective:

SVG has no perspective transform, so things on a receding wall (board, door, shelves, skirting,
ceiling line) are written as polygons through a projection. The wall is described in flat "wall
units" (u across, v down, same numbers as a frontal drawing); the vertical scale grows linearly
with u about the horizon, so verticals stay vertical and horizontals converge to one vanishing point.

    from persp import Wall
    w = Wall(horizon=520, k=0.00013, centre=960)   # k > 0: the wall comes toward the viewer on the right
    svg += w.box(628, 150, 1930, 620, fill="#a69ea6")          # a rectangle on the wall
    svg += w.line([(30, 680), (70, 680)])                       # a polyline on the wall
    cx, cy, rx, ry = w.ellipse(1676, 372, 38)                   # a circle on the wall

Run this file to print the projected corners of a rectangle:  python persp.py 628 150 1930 620
"""
from __future__ import annotations

import sys


class Wall:
    def __init__(self, horizon: float = 520.0, k: float = 0.00013, centre: float = 960.0):
        self.horizon, self.k, self.centre = horizon, k, centre

    def scale(self, u: float) -> float:
        return 1.0 + self.k * (u - self.centre)

    def xy(self, u: float, v: float) -> tuple[float, float]:
        return u, self.horizon + (v - self.horizon) * self.scale(u)

    def pt(self, u: float, v: float) -> str:
        x, y = self.xy(u, v)
        return f"{x:.1f} {y:.1f}"

    def quad(self, u0: float, v0: float, u1: float, v1: float) -> str:
        """Path data of a wall rectangle."""
        return f"M {self.pt(u0, v0)} L {self.pt(u1, v0)} L {self.pt(u1, v1)} L {self.pt(u0, v1)} Z"

    def poly(self, pts: list[tuple[float, float]], close: bool = True) -> str:
        d = " ".join(("M " if i == 0 else "L ") + self.pt(u, v) for i, (u, v) in enumerate(pts))
        return d + (" Z" if close else "")

    def box(self, u0, v0, u1, v1, fill: str, cls: str = "bg", extra: str = "") -> str:
        return f'<path class="{cls}" fill="{fill}" d="{self.quad(u0, v0, u1, v1)}"{extra}/>\n'

    def line(self, pts, cls: str = "bg", extra: str = "") -> str:
        return f'<path class="{cls}" fill="none" d="{self.poly(pts, close=False)}"{extra}/>\n'

    def ellipse(self, u: float, v: float, r: float) -> tuple[float, float, float, float]:
        """Centre and radii of a wall circle (width kept, height scaled)."""
        x, y = self.xy(u, v)
        return x, y, r, r * self.scale(u)

    def vanishing_x(self) -> float:
        return self.centre - 1.0 / self.k


class Camera:
    """A pinhole camera for whole rooms: every surface shares one horizon and one set of vanishing points.

    World: x to the right along the back wall, y up from the floor, z from the back wall toward the viewer.
    The camera has no pitch, so verticals stay vertical and the horizon is `centre[1]`.

        cam = Camera(pos=(1500, 280, 1700), yaw=16, f=1700)      # yaw > 0 turns the view to the left
        cam.quad3([(0, 0, 0), (400, 0, 0), (400, 300, 0), (0, 300, 0)])   # a rectangle on the back wall
        cam.box(1560, 2000, 0, 205, 200, 420)                    # visible faces of a box, back to front
        x, z = cam.floor_at(1000, 1012)                          # floor point under a screen point
    """

    def __init__(self, pos=(1500.0, 280.0, 1700.0), yaw: float = 16.0, f: float = 1700.0,
                 centre=(960.0, 520.0), near: float = 60.0):
        import math
        self.pos, self.f, self.centre, self.near = pos, f, centre, near
        t = math.radians(yaw)
        self.fwd = (-math.sin(t), 0.0, -math.cos(t))
        self.right = (math.cos(t), 0.0, -math.sin(t))

    def depth(self, x: float, y: float, z: float) -> float:
        d = (x - self.pos[0], y - self.pos[1], z - self.pos[2])
        return d[0] * self.fwd[0] + d[2] * self.fwd[2]

    def xy(self, x: float, y: float, z: float) -> tuple[float, float]:
        d = (x - self.pos[0], y - self.pos[1], z - self.pos[2])
        dep = max(self.near, d[0] * self.fwd[0] + d[2] * self.fwd[2])
        k = self.f / dep
        return (self.centre[0] + k * (d[0] * self.right[0] + d[2] * self.right[2]), self.centre[1] - k * d[1])

    def scale(self, x: float, y: float, z: float) -> float:
        """Screen pixels per world unit at this point."""
        return self.f / max(self.near, self.depth(x, y, z))

    def pt(self, x: float, y: float, z: float) -> str:
        sx, sy = self.xy(x, y, z)
        return f"{sx:.1f} {sy:.1f}"

    def poly3(self, pts, close: bool = True) -> str:
        d = " ".join(("M " if i == 0 else "L ") + self.pt(*q) for i, q in enumerate(pts))
        return d + (" Z" if close else "")

    quad3 = poly3

    def wall(self, u0: float, y0: float, u1: float, y1: float, z: float = 0.0) -> str:
        """Rectangle on a plane parallel to the back wall (y measured up from the floor)."""
        return self.poly3([(u0, y1, z), (u1, y1, z), (u1, y0, z), (u0, y0, z)])

    def floor(self, x0: float, z0: float, x1: float, z1: float, y: float = 0.0) -> str:
        """Rectangle on a horizontal plane (floor, table top, ceiling)."""
        return self.poly3([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)])

    def side(self, x: float, y0: float, y1: float, z0: float, z1: float) -> str:
        """Rectangle on a plane facing sideways (a box side, a side wall)."""
        return self.poly3([(x, y1, z0), (x, y1, z1), (x, y0, z1), (x, y0, z0)])

    def box(self, x0, x1, y0, y1, z0, z1) -> list[tuple[str, str]]:
        """Visible faces of an axis-aligned box as (name, path data), in paint order."""
        faces = []
        if self.pos[0] < x0:
            faces.append(("left", self.side(x0, y0, y1, z0, z1)))
        if self.pos[0] > x1:
            faces.append(("right", self.side(x1, y0, y1, z0, z1)))
        faces.append(("front", self.wall(x0, y0, x1, y1, z1)))
        if self.pos[1] > y1:
            faces.append(("top", self.floor(x0, z0, x1, z1, y1)))
        return faces

    def floor_at(self, sx: float, sy: float, y: float = 0.0) -> tuple[float, float]:
        """World (x, z) of the point on a horizontal plane that appears at a screen point."""
        dy = y - self.pos[1]
        dep = -self.f * dy / (sy - self.centre[1])
        lat = (sx - self.centre[0]) * dep / self.f
        dx = lat * self.right[0] + dep * self.fwd[0]
        dz = lat * self.right[2] + dep * self.fwd[2]
        return self.pos[0] + dx, self.pos[2] + dz


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    w = Wall()
    print(w.quad(*[float(a) for a in sys.argv[1:]]))
    print(f"vanishing point x = {w.vanishing_x():.0f}, horizon y = {w.horizon:.0f}")
