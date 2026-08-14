"""Vectorised gradient noise over numpy grids.

The `noise` package on this machine is scalar per call; five million calls is not
a sensible way to build a heightfield. This is Perlin gradient noise evaluated on
whole arrays at once, plus the two things terrain actually needs on top of it:
ridged multifractal (for anything erosional) and domain warping (which is what
stops fbm looking like fbm).

Everything is seeded. The world must be rebuildable byte for byte.
"""
import numpy as np

_GRAD2 = np.array([
    (1, 1), (-1, 1), (1, -1), (-1, -1),
    (1, 0), (-1, 0), (0, 1), (0, -1),
], dtype=np.float32)
_GRAD2 /= np.linalg.norm(_GRAD2, axis=1, keepdims=True)


def _perm(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    p = rng.permutation(256).astype(np.int32)
    return np.concatenate([p, p])


def _fade(t):
    # Quintic — C2 continuous, so no visible lattice creases in the derivative.
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def perlin(x: np.ndarray, y: np.ndarray, seed: int = 0) -> np.ndarray:
    """Perlin gradient noise in roughly [-1, 1]. x, y are grids in lattice units."""
    p = _perm(seed)
    xi = np.floor(x).astype(np.int32)
    yi = np.floor(y).astype(np.int32)
    xf = (x - xi).astype(np.float32)
    yf = (y - yi).astype(np.float32)
    xi &= 255
    yi &= 255

    def grad_dot(ix, iy, dx, dy):
        h = p[(p[ix & 255] + (iy & 255)) & 511] & 7
        g = _GRAD2[h]
        return g[..., 0] * dx + g[..., 1] * dy

    n00 = grad_dot(xi,     yi,     xf,       yf)
    n10 = grad_dot(xi + 1, yi,     xf - 1.0, yf)
    n01 = grad_dot(xi,     yi + 1, xf,       yf - 1.0)
    n11 = grad_dot(xi + 1, yi + 1, xf - 1.0, yf - 1.0)

    u = _fade(xf)
    v = _fade(yf)
    a = n00 + u * (n10 - n00)
    b = n01 + u * (n11 - n01)
    return (a + v * (b - a)) * 1.4142


def fbm(x, y, seed=0, octaves=6, lacunarity=2.0, gain=0.5):
    """Fractional Brownian motion. The default for anything that should look
    like it has structure at every scale at once."""
    total = np.zeros_like(x, dtype=np.float32)
    amp, freq, norm = 1.0, 1.0, 0.0
    for o in range(octaves):
        total += amp * perlin(x * freq, y * freq, seed + o * 7919)
        norm += amp
        amp *= gain
        freq *= lacunarity
    return total / norm


def ridged(x, y, seed=0, octaves=6, lacunarity=2.0, gain=0.5, sharpness=1.0):
    """Ridged multifractal — creases where fbm has zero crossings. This is what
    makes a hillside read as eroded rather than lumpy, because real relief is
    made of ridges and valleys, not blobs."""
    total = np.zeros_like(x, dtype=np.float32)
    amp, freq, norm, prev = 1.0, 1.0, 0.0, np.ones_like(x, dtype=np.float32)
    for o in range(octaves):
        n = perlin(x * freq, y * freq, seed + o * 6151)
        n = 1.0 - np.abs(n)
        n = n ** (1.0 + sharpness)
        total += amp * n * prev
        prev = np.clip(n, 0.0, 1.0)
        norm += amp
        amp *= gain
        freq *= lacunarity
    return (total / norm) * 2.0 - 1.0


def warp(x, y, seed=0, strength=1.0, octaves=4):
    """Domain warp. Offsetting the sample position by more noise is the single
    cheapest way to stop noise looking like noise — it breaks the axis-aligned
    smear that plain fbm always has."""
    wx = fbm(x + 13.7, y - 4.1, seed + 101, octaves=octaves)
    wy = fbm(x - 7.3, y + 19.9, seed + 211, octaves=octaves)
    return x + wx * strength, y + wy * strength


def grid_coords(w: int, h: int, cell: float, scale_m: float, offset=(0.0, 0.0)):
    """Lattice coordinates for a w×h grid of `cell`-metre cells, where one noise
    lattice unit spans `scale_m` metres."""
    gx = (np.arange(w, dtype=np.float32) * cell + offset[0]) / scale_m
    gy = (np.arange(h, dtype=np.float32) * cell + offset[1]) / scale_m
    return np.meshgrid(gx, gy)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / max(1e-6, (e1 - e0)), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)
