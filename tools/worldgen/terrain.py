"""The heightfield.

Order matters, because each step is a physical process acting on the result of
the last one:

  1. relief      — hand-placed masses (the hills are where the city's story needs
                   them, and a hill is not a procedural accident)
  2. roughness   — ridged multifractal, domain-warped, scaled by local relief so
                   the flats stay flat
  3. coast blend — land is forced to zero at the shoreline over a width that
                   varies from 12 m (rock, so: cliff) to 140 m (sand, so: beach)
  4. erosion     — stream-power incision driven by real flow routing, plus
                   hillslope creep. This is what puts a dendritic drainage
                   pattern on the hillsides and cuts the valleys the roads will
                   later follow. Noise cannot produce this; it has no history.
  5. bathymetry  — the drowned valley, the shelf, the lagoon
  6. human work  — reclaimed flats, cut platforms, the quarry, the river channel.
                   These are flat and hard-edged because people made them so.
"""
import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt
from skimage.morphology import reconstruction
from PIL import Image, ImageDraw

from . import config as C
from .noisefield import fbm, ridged, warp, smoothstep, perlin


# ---------------------------------------------------------------------------
# 1–3  land surface
# ---------------------------------------------------------------------------
def _relief(wx, wz):
    h = np.zeros_like(wx, dtype=np.float32)
    for (cx, cz, r, peak, expo) in C.HILLS:
        d = np.hypot(wx - cx, wz - cz) / r
        h += peak * np.clip(1.0 - d, 0.0, 1.0) ** expo
    return h


def _shore_width(wx, wz):
    """How far inland the land takes to climb away from the water.

    Narrow means rock and a cliff; wide means sand and a beach. It is a noise
    field rather than a constant because a real coast alternates between them,
    and it is forced wide around the spit and the lagoon, which are sand by
    definition — the spit exists *because* sand accumulated there.
    """
    n = fbm(wx / 620.0, wz / 620.0, C.SEED + 77, octaves=4)
    w = 14.0 + (n * 0.5 + 0.5) ** 1.6 * 150.0
    sandy = smoothstep(1150.0, 1500.0, wz)                       # lagoon and spit
    w = w * (1.0 - sandy) + np.maximum(w, 130.0) * sandy
    cliffy = smoothstep(-900.0, -1350.0, wz) * smoothstep(600.0, 1200.0, wx)
    w = w * (1.0 - cliffy) + np.minimum(w, 22.0) * cliffy        # Sarn Head cliffs
    return w


def land_surface(f):
    wx, wz, sdf = f['wx'], f['wz'], f['sdf']

    base = _relief(wx, wz)

    # Roughness, domain-warped so it doesn't read as fbm. Ridged where there is
    # relief to erode, gentler fbm on the low ground.
    nx, nz = warp(wx / 340.0, wz / 340.0, C.SEED + 5, strength=0.55)
    r = ridged(nx, nz, C.SEED + 13, octaves=7, sharpness=0.9)
    s = fbm(wx / 130.0, wz / 130.0, C.SEED + 29, octaves=5)

    relief_amt = smoothstep(6.0, 46.0, base)          # only tall ground gets ridges
    h = base + r * 15.0 * relief_amt + s * (1.8 + 5.0 * relief_amt)

    # A gentle swell inland so the low ground isn't a plane.
    h += smoothstep(0.0, 420.0, sdf) * 3.4

    # Force the land to meet the water at zero.
    blend = smoothstep(0.0, 1.0, np.clip(sdf / _shore_width(wx, wz), 0.0, 1.0))
    h = np.maximum(h, 0.35) * blend

    return h.astype(np.float32)


# ---------------------------------------------------------------------------
# 4  erosion
# ---------------------------------------------------------------------------
def _fill_depressions(h):
    """Priority-flood via greyscale reconstruction. Flow routing needs a DEM
    with no interior sinks or the accumulation gets stuck in pits."""
    seed = np.full_like(h, h.max())
    seed[1:-1, 1:-1] = h[1:-1, 1:-1]
    seed = np.maximum(seed, h)
    seed[0, :] = h[0, :]; seed[-1, :] = h[-1, :]
    seed[:, 0] = h[:, 0]; seed[:, -1] = h[:, -1]
    return reconstruction(seed, h, method='erosion').astype(np.float32)


_D8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _flow(h, cell):
    """D8 steepest-descent receivers and drainage area, on a filled DEM."""
    gh, gw = h.shape
    hp = np.pad(h, 1, mode='edge')
    best_slope = np.zeros((gh, gw), np.float32)
    best_rx = np.zeros((gh, gw), np.int32)
    best_rz = np.zeros((gh, gw), np.int32)
    zz, xx = np.mgrid[0:gh, 0:gw]

    for (dz, dx) in _D8:
        nb = hp[1 + dz: 1 + dz + gh, 1 + dx: 1 + dx + gw]
        dist = cell * (1.4142 if dz and dx else 1.0)
        slope = (h - nb) / dist
        better = slope > best_slope
        best_slope = np.where(better, slope, best_slope)
        best_rz = np.where(better, np.clip(zz + dz, 0, gh - 1), best_rz)
        best_rx = np.where(better, np.clip(xx + dx, 0, gw - 1), best_rx)

    # Accumulate area downstream, processing cells from high to low.
    area = np.full((gh, gw), cell * cell, np.float32)
    order = np.argsort(h, axis=None)[::-1]
    flat_rec = (best_rz * gw + best_rx).ravel()
    flat_area = area.ravel()
    flat_slope = best_slope.ravel()
    for i in order:
        if flat_slope[i] > 0.0:
            flat_area[flat_rec[i]] += flat_area[i]
    return best_slope, flat_area.reshape(gh, gw)


def erode(h, land, cell, iters=None):
    """Stream-power incision + hillslope diffusion.

    dh/dt = -K · A^m · S^n  on land, plus a diffusion term for creep. This is
    the standard landscape-evolution formulation, and it is worth the wall clock
    because it is the only step that gives the terrain a *history*: valleys that
    join, ridges between them, and slopes that steepen towards the divides.
    """
    iters = C.EROSION_ITERS if iters is None else iters
    h = h.astype(np.float32).copy()
    mask = land.astype(np.float32)
    for it in range(iters):
        filled = _fill_depressions(h)
        slope, area = _flow(filled, cell)
        incision = C.EROSION_K * (area ** C.EROSION_M) * (slope ** C.EROSION_N)
        # Never cut below the sea, and never erode what is already underwater.
        h = h - np.minimum(incision, h * 0.35) * mask
        creep = gaussian_filter(h, 1.0) - h
        h = h + creep * C.EROSION_DIFFUSE * mask
        h = np.maximum(h, 0.0) * mask
    return h


# ---------------------------------------------------------------------------
# 5  bathymetry
# ---------------------------------------------------------------------------
def _poly_mask(poly, gw, gh, cell, mnx, mnz, blur=6.0):
    img = Image.new('L', (gw, gh), 0)
    px = [((x - mnx) / cell, (z - mnz) / cell) for (x, z) in poly]
    ImageDraw.Draw(img).polygon(px, fill=255)
    m = np.asarray(img, dtype=np.float32) / 255.0
    return gaussian_filter(m, blur)


def bathymetry(f):
    """Under the water. Deep water hard against the south shore is the reason
    the city exists, so it is modelled rather than assumed."""
    sdf, sound_d, sound_t = f['sdf'], f['sound_d'], f['sound_t']
    wx, wz = f['wx'], f['wz']
    off = np.maximum(0.0, -sdf)     # metres offshore

    # Continental shelf: falls away from the shore, flattening out.
    shelf = -C.OCEAN_SHELF_DEPTH * -1.0
    depth = C.OCEAN_SHELF_DEPTH * smoothstep(0.0, 900.0, off)

    # The drowned valley. Deepest at the mouth, silting towards the head, with a
    # steep-sided trough — that is what a ria cross-section looks like.
    thal = C.SOUND_DEPTH_HEAD + (C.SOUND_DEPTH_MOUTH - C.SOUND_DEPTH_HEAD) * (1.0 - sound_t)
    across = np.clip(sound_d / C.SOUND_HALF_WIDTH, 0.0, 1.0)
    trough = thal * (1.0 - across ** 1.7)
    in_sound = smoothstep(1.0, 0.55, across) * smoothstep(0.0, 40.0, off)
    depth = np.minimum(depth, trough * in_sound + depth * (1.0 - in_sound))

    # The lagoon: shallow everywhere, because it is a drift-built basin.
    lag = _poly_mask(C.LAGOON_POLY, C.GRID_W, C.GRID_H, C.CELL,
                     C.WORLD_MIN_X, C.WORLD_MIN_Z, blur=10.0)
    lagoon_bed = C.LAGOON_DEPTH * smoothstep(0.0, 120.0, off) - 0.4
    depth = depth * (1.0 - lag) + lagoon_bed * lag

    # Sandbanks and channels in the shallows — the water is never a flat plane.
    ripple = fbm(wx / 210.0, wz / 210.0, C.SEED + 401, octaves=5)
    depth += ripple * np.clip(2.6 + off * 0.004, 0.0, 5.5) * smoothstep(0.0, 60.0, off)

    return np.minimum(depth, -0.05).astype(np.float32)


# ---------------------------------------------------------------------------
# 6  what people did to it
# ---------------------------------------------------------------------------
def human_works(h, f):
    """Made ground, cut platforms, the quarry and the river channel.

    Flat, hard-edged and level to the centimetre, because that is what
    engineering looks like next to a hillside that isn't."""
    wx, wz = f['wx'], f['wz']
    h = h.copy()

    for (x0, z0, x1, z1, height, soft, name) in C.PLATFORMS:
        # Rounded-rectangle falloff, plus a little noise on the edge so the
        # boundary isn't a perfect rectangle where fill met natural ground.
        edge_noise = perlin(wx / 55.0, wz / 55.0, C.SEED + 611) * soft * 0.6
        dx = np.maximum(x0 - wx, wx - x1)
        dz = np.maximum(z0 - wz, wz - z1)
        d = np.maximum(dx, dz) + edge_noise
        m = 1.0 - smoothstep(-soft, soft, d)
        # Reclaimed land is flat but not perfectly flat: it settles.
        settle = fbm(wx / 180.0, wz / 180.0, C.SEED + 733, octaves=3) * 0.35
        h = h * (1.0 - m) + (height + settle) * m

    q = C.QUARRY
    dq = np.hypot(wx - q['cx'], wz - q['cz'])
    benches = np.floor(np.clip((dq - q['r'] * 0.35) / 26.0, 0, 8)) * 7.0
    pit = q['floor'] + benches
    m = 1.0 - smoothstep(q['r'] * 0.55, q['r'], dq)
    h = np.minimum(h, h * (1.0 - m) + pit * m)

    # The river: a channel graded down to the basin, with a floodplain either
    # side that is flat because it floods.
    rd, rt = f['river_d'], f['river_t']
    width = C.RIVER_WIDTH_HEAD + (C.RIVER_WIDTH_MOUTH - C.RIVER_WIDTH_HEAD) * (1.0 - rt)
    bed = 0.6 + rt * 9.0
    chan = 1.0 - smoothstep(width * 0.5, width * 0.5 + 26.0, rd)
    h = h * (1.0 - chan) + np.minimum(h, bed - 2.2) * chan
    flood = (1.0 - smoothstep(width, width + 260.0, rd)) * (1.0 - chan)
    h = h * (1.0 - flood * 0.75) + (bed + 1.9) * flood * 0.75

    return h.astype(np.float32)


# ---------------------------------------------------------------------------
def build(f):
    """Full pipeline. Returns the height in metres above sea level everywhere,
    land and seabed in one field."""
    import time
    t0 = time.time()

    h = land_surface(f)
    print(f'  land surface        {time.time()-t0:5.1f}s  max {h.max():6.1f} m')

    # Erode on the coarse grid, then put the detail back.
    ez, ex = C.EROSION_H, C.EROSION_W
    h_small = np.asarray(Image.fromarray(h).resize((ex, ez), Image.BILINEAR))
    land_small = np.asarray(
        Image.fromarray((f['land'] * 255).astype(np.uint8)).resize((ex, ez), Image.BILINEAR)
    ) > 127
    t1 = time.time()
    h_small = erode(h_small, land_small, C.EROSION_CELL)
    print(f'  erosion {C.EROSION_ITERS:>3} iters  {time.time()-t1:5.1f}s  max {h_small.max():6.1f} m')

    h_eroded = np.asarray(
        Image.fromarray(h_small).resize((C.GRID_W, C.GRID_H), Image.BICUBIC)
    ).astype(np.float32)

    # Keep the fine detail that the coarse pass could not carry, but only where
    # erosion did not do much — otherwise the valleys get filled back in.
    h_base_small = np.asarray(
        Image.fromarray(h).resize((ex, ez), Image.BILINEAR))
    removed = np.asarray(Image.fromarray(
        (h_base_small - h_small).astype(np.float32)
    ).resize((C.GRID_W, C.GRID_H), Image.BICUBIC)).astype(np.float32)
    detail = (h - gaussian_filter(h, 3.0)) * np.clip(1.0 - removed / 12.0, 0.15, 1.0)
    h = h_eroded + detail
    h = np.maximum(h, 0.0) * f['land']

    h = human_works(h, f)
    h = np.maximum(h, 0.0) * f['land']

    sea = bathymetry(f)
    out = np.where(f['land'], np.maximum(h, 0.05), sea).astype(np.float32)
    print(f'  total               {time.time()-t0:5.1f}s')
    return out
