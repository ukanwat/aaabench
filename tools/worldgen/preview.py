"""Look at the data before anything is built from it.

A generator's output is a proposal. These renders are how the proposal gets
inspected: a shaded relief map that reads like an aerial photograph, a
bathymetric section across the harbour, and a slope map — because a gradient
nothing can climb is invisible in a height map and obvious in a slope map.
"""
import numpy as np
from PIL import Image

from . import config as C


def hillshade(h, cell, az_deg=315.0, alt_deg=42.0):
    gz, gx = np.gradient(h.astype(np.float32), cell)
    slope = np.arctan(np.hypot(gx, gz))
    aspect = np.arctan2(-gz, gx)
    az = np.radians(360.0 - az_deg + 90.0)
    alt = np.radians(alt_deg)
    shade = (np.sin(alt) * np.cos(slope) +
             np.cos(alt) * np.sin(slope) * np.cos(az - aspect))
    return np.clip(shade, 0.0, 1.0)


_LAND_RAMP = [
    (0.0,   (118, 124,  92)),
    (6.0,   (104, 116,  78)),
    (18.0,  ( 96, 108,  70)),
    (45.0,  (110, 108,  80)),
    (80.0,  (128, 122,  98)),
    (120.0, (152, 148, 132)),
]
_SEA_RAMP = [
    (0.0,   (108, 148, 160)),
    (-2.0,  ( 66, 116, 138)),
    (-8.0,  ( 38,  84, 114)),
    (-20.0, ( 22,  56,  86)),
    (-40.0, ( 12,  34,  60)),
]


def _ramp(vals, stops):
    xs = np.array([s[0] for s in stops], dtype=np.float32)
    cols = np.array([s[1] for s in stops], dtype=np.float32)
    if xs[0] > xs[-1]:
        xs, cols = xs[::-1], cols[::-1]
    out = np.empty(vals.shape + (3,), dtype=np.float32)
    for c in range(3):
        out[..., c] = np.interp(vals, xs, cols[:, c])
    return out


def aerial(h, cell=None, out='preview.png', scale=1):
    """A shaded, coloured, hypsometric render — the map read as a picture."""
    cell = cell or C.CELL
    land = h > 0.0
    col = np.where(land[..., None], _ramp(h, _LAND_RAMP), _ramp(h, _SEA_RAMP))

    sh = hillshade(h, cell)
    # Only shade the land; shading the seabed would draw the bathymetry as if it
    # were visible, which it is not.
    lit = np.where(land[..., None], col * (0.42 + 0.86 * sh[..., None]), col)

    # A pale line exactly on the waterline, so the silhouette is legible.
    edge = (np.abs(h) < 0.9) & (h > -2.0)
    lit[edge] = np.array([232, 226, 208], dtype=np.float32)

    img = Image.fromarray(np.clip(lit, 0, 255).astype(np.uint8))
    if scale != 1:
        img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)
    img.save(out)
    return out


def slope_map(h, cell=None, out='slope.png', warn_pct=12.0):
    """Gradient in percent, with anything a road could not climb flagged red."""
    cell = cell or C.CELL
    gz, gx = np.gradient(h.astype(np.float32), cell)
    pct = np.hypot(gx, gz) * 100.0
    img = np.zeros(h.shape + (3,), dtype=np.float32)
    t = np.clip(pct / (warn_pct * 2.0), 0, 1)
    img[..., 1] = 60 + 160 * (1 - t)
    img[..., 2] = 60 + 120 * (1 - t)
    img[..., 0] = 40 + 200 * t
    img[pct > warn_pct * 2.5] = np.array([255, 40, 40], dtype=np.float32)
    img[h <= 0.0] = np.array([16, 26, 40], dtype=np.float32)
    Image.fromarray(img.astype(np.uint8)).save(out)
    return out


def section(h, z_world, out='section.png', width=1400, height=420):
    """A cross-section at a given world Z. Reading a harbour's depth off a
    section is the only way to know the deep water is actually where the story
    says it is."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    row = int((z_world - C.WORLD_MIN_Z) / C.CELL)
    row = max(0, min(C.GRID_H - 1, row))
    prof = h[row]
    xs = np.arange(C.GRID_W) * C.CELL + C.WORLD_MIN_X

    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    ax.fill_between(xs, prof, -60, where=prof > 0, color='#6b6f52')
    ax.fill_between(xs, 0, -60, color='#2a4f6e', alpha=0.55)
    ax.plot(xs, prof, color='#22252b', lw=1.0)
    ax.axhline(0, color='#dfe6ee', lw=0.8)
    ax.set_ylim(-45, 140)
    ax.set_xlim(xs[0], xs[-1])
    ax.set_title(f'Ashmouth — section at z = {z_world:.0f} m   (vertical exaggeration ~6×)')
    ax.set_xlabel('x (m, east)'); ax.set_ylabel('elevation (m)')
    ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return out


def stats(h, f):
    cell_area = C.CELL * C.CELL
    land = h > 0.0
    total_land = land.sum() * cell_area / 1e6
    gz, gx = np.gradient(h.astype(np.float32), C.CELL)
    pct = np.hypot(gx, gz) * 100.0
    lp = pct[land]
    lines = [
        f'land area          {total_land:8.2f} km²  of {C.WORLD_W*C.WORLD_H/1e6:.1f} km² world',
        f'  mainland         {(f["coverage"] >= 0.5).sum()*cell_area/1e6:8.2f} km² (all masses, incl. islets)',
        f'highest point      {h.max():8.1f} m',
        f'deepest water      {h.min():8.1f} m',
        f'buildable (<8%)    {(lp < 8).sum()*cell_area/1e6:8.2f} km²  ({100*(lp<8).mean():.0f}% of land)',
        f'steep (>25%)       {(lp > 25).sum()*cell_area/1e6:8.2f} km²  ({100*(lp>25).mean():.0f}% of land)',
        f'median land slope  {np.median(lp):8.1f} %',
        f'coastline cells    {int((np.abs(h) < 1.0).sum()):8d}',
    ]
    return '\n'.join(lines)
