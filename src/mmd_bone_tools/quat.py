"""Tiny quaternion helpers. Quaternions are (x, y, z, w) tuples, as in VMD."""

from __future__ import annotations

import math

IDENTITY = (0.0, 0.0, 0.0, 1.0)


def mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def conj(q):
    return (-q[0], -q[1], -q[2], q[3])


def normalize(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)


def rotate(q, v):
    x, y, z, _ = mul(mul(q, (v[0], v[1], v[2], 0.0)), conj(q))
    return (x, y, z)


def from_axis_angle(axis, angle):
    n = math.sqrt(sum(c * c for c in axis)) or 1.0
    s = math.sin(angle / 2) / n
    return (axis[0] * s, axis[1] * s, axis[2] * s, math.cos(angle / 2))


def between(u, v):
    """Shortest-arc rotation taking direction u onto direction v."""
    nu = math.sqrt(sum(c * c for c in u))
    nv = math.sqrt(sum(c * c for c in v))
    if nu == 0 or nv == 0:
        return IDENTITY
    u = [c / nu for c in u]
    v = [c / nv for c in v]
    d = sum(a * b for a, b in zip(u, v))
    if d < -0.999999:
        axis = (1.0, 0.0, 0.0) if abs(u[0]) < 0.9 else (0.0, 1.0, 0.0)
        cx = (u[1] * axis[2] - u[2] * axis[1], u[2] * axis[0] - u[0] * axis[2],
              u[0] * axis[1] - u[1] * axis[0])
        return from_axis_angle(cx, math.pi)
    c = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    return normalize((c[0], c[1], c[2], 1.0 + d))


def angle(q) -> float:
    w = max(-1.0, min(1.0, abs(q[3])))
    return 2 * math.acos(w)


def is_identity(q, tol_rad: float = 1e-4) -> bool:
    return angle(q) < tol_rad
