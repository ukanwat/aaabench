"""The land, built the way land is built.

    uplift → relief → valley → EROSION at glacial base level → flood → deposition → human works

The coastline is not authored anywhere in this file. It is wherever the finished
surface crosses zero, which is what makes the bays drowned tributaries, the
headlands the ridges between them, and the islands hills the water went round.
"""
import time

import numpy as np
from scipy.interpolate import splprep, splev
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter, distance_transform_edt, binary_fill_holes
from skimage.morphology import reconstruction, remove_small_objects
from PIL import Image, ImageDraw

from . import config as C
from .noisefield import fbm, ridged, warp, smoothstep, perlin


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def world_grid(w=None, h=None, cell=None):
    w = w or C.GRID_W; h = h or C.GRID_H; cell = cell or C.CELL
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    return xx * cell + C.WORLD_MIN_X, yy * cell + C.WORLD_MIN_Z


def _rot(wx, wz, cx, cz, deg):
    a = np.radians(deg)
    dx, dz = wx - cx, wz - cz
    return dx * np.cos(a) - dz * np.sin(a), dx * np.sin(a) + dz * np.cos(a)


def _poly_mask(poly, wx, wz=None, blur=0.0, cell=None, jitter=0.0, seed=0):
    """Polygon → mask, with the edge broken up by noise.

    A clean polygon edge is visible from the air as a straight line across the
    ground, and every hand-drawn region in the world inherits it. Real fill
    lines, quarry rims and yard boundaries wander: they were made in stages by
    different people and they follow whatever was in the way. Jittering the
    threshold is one rule that fixes every region at once.
    """
    cell = cell or C.CELL
    gh, gw = wx.shape
    img = Image.new('L', (gw, gh), 0)
    px = [((x - C.WORLD_MIN_X) / cell, (z - C.WORLD_MIN_Z) / cell) for (x, z) in poly]
    ImageDraw.Draw(img).polygon(px, fill=255)
    m = np.asarray(img, dtype=np.float32) / 255.0
    if blur > 0:
        m = gaussian_filter(m, blur)
    if jitter > 0.0 and wz is not None:
        n = fbm(wx / 60.0, wz / 60.0, C.SEED + seed, octaves=4) * 0.5 + 0.5
        edge = gaussian_filter(m, max(2.0, jitter))
        m = np.clip((edge - 0.5) * 6.0 + 0.5 + (n - 0.5) * 1.1, 0.0, 1.0)
    return m


def _spline(pts, n=1600):
    p = np.asarray(pts, dtype=np.float64)
    tck, _ = splprep([p[:, 0], p[:, 1]], s=0, k=3)
    u = np.linspace(0, 1, n)
    sx, sy = splev(u, tck)
    return np.asarray(sx), np.asarray(sy), u


def _line_fields(pts, wx, wz, cell=None, n=4000):
    """Distance to a splined polyline, and how far along it the nearest point is.

    Queried against a KD-tree of dense spline samples rather than rasterising the
    line. Rasterising was wrong twice over: the in-fill pixels a line drawer emits
    between samples carry no position-along value, so ~0.7% of the map inherited
    t = 0 — which at the head of the valley means +26 m instead of −30 m, i.e. a
    56 m spike, thirty-five thousand times. And a raster distance is quantised to
    the cell, which puts stair-steps on every curve derived from it.
    """
    sx, sy, u = _spline(pts, n)
    tree = cKDTree(np.column_stack([sx, sy]))
    q = np.column_stack([wx.ravel(), wz.ravel()])
    dist, idx = tree.query(q, workers=-1)
    return (dist.reshape(wx.shape).astype(np.float32),
            u[idx].reshape(wx.shape).astype(np.float32))


def _curve(table, t):
    ts = np.array([p[0] for p in table], dtype=np.float32)
    vs = np.array([p[1] for p in table], dtype=np.float32)
    return np.interp(t, ts, vs).astype(np.float32)


# ---------------------------------------------------------------------------
# 1  uplift — the structural high ground
# ---------------------------------------------------------------------------
def uplift(wx, wz):
    deep = C.GLACIAL_SEA_LEVEL - 18.0
    h = np.full(wx.shape, deep, dtype=np.float32)

    for m in C.MASSIFS:
        cx, cz = m['c']
        rx, rz = m['r']
        dx, dz = _rot(wx, wz, cx, cz, m['rot'])
        d = np.hypot(dx / rx, dz / rz)
        # Irregular rim: warp the radius with noise so no massif is an ellipse.
        wob = fbm(wx / 520.0, wz / 520.0, C.SEED + int(cx) % 977, octaves=4)
        d = d * (1.0 + wob * m['irr'])
        # Smoothstep has zero gradient at BOTH ends, so the rim is genuinely
        # shallow — which is what lets the relief noise swing the waterline
        # hundreds of metres and produce an indented coast. `shape` below 1
        # fills the profile out towards a plateau, above 1 makes it peakier.
        #
        # The previous form, (1 − d) ** (1/flat) with flat > 1, gave an exponent
        # BELOW one, whose gradient goes to infinity at the rim: a cliff edge and
        # a tableland interior — the exact opposite of the intent.
        prof = smoothstep(1.0, 0.0, d) ** m['shape']
        # Interpolate between the deep floor and the peak, so `peak` really is
        # the summit height above today's sea level and the waterline lands
        # where the profile crosses it. Adding a fraction of the peak to a floor
        # 58 m down instead put only the inner third of each massif above water.
        h = np.maximum(h, deep + (m['peak'] - deep) * prof)

    for r in C.RESISTANT:
        cx, cz = r['c']
        rx, rz = r['r']
        dx, dz = _rot(wx, wz, cx, cz, r['rot'])
        d = np.hypot(dx / rx, dz / rz)
        h += r['add'] * np.clip(1.0 - d, 0.0, 1.0) ** 1.4

    return h


# ---------------------------------------------------------------------------
# 2  relief
# ---------------------------------------------------------------------------
def relief(wx, wz, base):
    R = C.RELIEF
    nx, nz = warp(wx / R['major_wavelength'], wz / R['major_wavelength'],
                  C.SEED + 5, strength=R['warp'])
    major = ridged(nx, nz, C.SEED + 13, octaves=5, sharpness=0.7)
    mid = fbm(wx / R['mid_wavelength'], wz / R['mid_wavelength'], C.SEED + 29, octaves=4)
    fine = fbm(wx / R['fine_wavelength'], wz / R['fine_wavelength'], C.SEED + 47, octaves=3)

    # Scale relief with how far above the glacial sea floor the ground is: the
    # deep shelf stays smooth, the uplands get ridged.
    amt = smoothstep(C.GLACIAL_SEA_LEVEL - 10.0, C.GLACIAL_SEA_LEVEL + 55.0, base)
    return (major * R['major_amp'] * (0.35 + 0.65 * amt)
            + mid * R['mid_amp'] * (0.5 + 0.5 * amt)
            + fine * R['fine_amp'])


# ---------------------------------------------------------------------------
# 3  the valley
# ---------------------------------------------------------------------------
def _valley_centreline_z(wx):
    """z of the valley centre as a continuous function of x. Used only to decide
    which shore a point is on — the north side is steep, the south side is the
    one the city could be built on."""
    sx, sy, _ = _spline(C.VALLEY, 4000)
    order = np.argsort(sx)
    return np.interp(wx, sx[order], sy[order]).astype(np.float32)


def carve_valley(h, wx, wz, cell=None):
    d, _t = _line_fields(C.VALLEY, wx, wz, cell=cell)

    # Parameterise DOWN the valley by x, not by position-along-the-curve.
    # Nearest-point-on-curve is discontinuous across the curve's medial axis, so
    # anything driven by it jumps there — which showed up as a straight-edged
    # wedge sliced out of the north shore wherever the valley bends. The valley
    # runs monotonically west to east, so x is a continuous parameter over the
    # whole map and the discontinuity cannot exist.
    t = np.clip((wx - C.WORLD_MIN_X) / C.WORLD_W, 0.0, 1.0)
    floor = _curve(C.VALLEY_FLOOR, t)
    half = _curve(C.VALLEY_WIDTH, t)

    # Sinuosity, so the floor is not a swept profile down a spline.
    wobble = fbm(wx / 260.0, wz / 260.0, C.SEED + 313, octaves=3) * 30.0
    d = np.maximum(0.0, d + wobble)

    # Cross-section: a floor, then sides climbing to the upland over a run that
    # varies along the valley — a drowned valley has steep sides, but not
    # uniformly steep ones.
    zc = _valley_centreline_z(wx)
    north = wz < zc
    run = np.where(north, C.VALLEY_SIDE_RUN_N, C.VALLEY_SIDE_RUN_S)
    # Short run through the resistant band: that is what makes the Narrows a
    # gorge rather than just another part of the channel.
    run = run * _curve(C.VALLEY_SIDE_RUN_SCALE, t)
    run = run * (1.0 + 0.35 * fbm(wx / 430.0, wz / 430.0, C.SEED + 317, octaves=3))
    # NOT clamped at the top. The valley surface has to keep climbing past the
    # valley so that `minimum` becomes a no-op out on the uplands — clamping s
    # to 1 plateaus the surface at floor + SIDE_HEIGHT and then quietly shaves
    # every summit in the world down to it (North Point went from 126 m to 35 m).
    s = np.maximum(0.0, (d - half) / np.maximum(60.0, run))
    valley = floor + C.VALLEY_SIDE_HEIGHT * s ** 1.45
    return np.minimum(h, valley).astype(np.float32)


# ---------------------------------------------------------------------------
# 4  erosion
# ---------------------------------------------------------------------------
def _fill_depressions(h):
    seed = np.full_like(h, h.max())
    seed[1:-1, 1:-1] = h[1:-1, 1:-1]
    seed = np.maximum(seed, h)
    seed[0, :] = h[0, :]; seed[-1, :] = h[-1, :]
    seed[:, 0] = h[:, 0]; seed[:, -1] = h[:, -1]
    return reconstruction(seed, h, method='erosion').astype(np.float32)


_D8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _flow(h, cell):
    gh, gw = h.shape
    hp = np.pad(h, 1, mode='edge')
    best_slope = np.zeros((gh, gw), np.float32)
    best_i = np.arange(gh * gw, dtype=np.int64).reshape(gh, gw)
    zz, xx = np.mgrid[0:gh, 0:gw]

    for (dz, dx) in _D8:
        nb = hp[1 + dz: 1 + dz + gh, 1 + dx: 1 + dx + gw]
        dist = cell * (1.4142 if dz and dx else 1.0)
        slope = (h - nb) / dist
        better = slope > best_slope
        best_slope = np.where(better, slope, best_slope)
        nz = np.clip(zz + dz, 0, gh - 1)
        nx = np.clip(xx + dx, 0, gw - 1)
        best_i = np.where(better, nz * gw + nx, best_i)

    area = np.full(gh * gw, cell * cell, np.float32)
    rec = best_i.ravel()
    slp = best_slope.ravel()
    order = np.argsort(h, axis=None)[::-1]
    for i in order.tolist():
        if slp[i] > 0.0:
            area[rec[i]] += area[i]
    return best_slope, area.reshape(gh, gw)


def erode(h, cell, iters=None, base_level=None):
    """Stream-power incision against a base level, plus hillslope creep.

    Run against the GLACIAL sea level, not today's. That is the whole trick:
    the valleys get cut to a shoreline 40 m lower than the present one, and then
    the flood drowns them."""
    iters = C.EROSION_ITERS if iters is None else iters
    base = C.GLACIAL_SEA_LEVEL if base_level is None else base_level
    h = h.astype(np.float32).copy()
    for _ in range(iters):
        above = (h > base).astype(np.float32)
        filled = _fill_depressions(h)
        slope, area = _flow(filled, cell)
        incision = C.EROSION_K * (area ** C.EROSION_M) * (slope ** C.EROSION_N)
        headroom = np.maximum(0.0, h - base)
        h = h - np.minimum(incision, headroom * 0.4) * above
        h = h + (gaussian_filter(h, 1.0) - h) * C.EROSION_DIFFUSE * above
    return h


# ---------------------------------------------------------------------------
# 5  deposition — what the sea and the river put back
# ---------------------------------------------------------------------------
def _drift_line(h, wx, wz):
    """Where longshore drift would actually build a bar.

    Derived from the coast that exists rather than hand-placed beside a coast
    that was imagined: take the southern shoreline, smooth it hard (drift does
    not follow every cove — it cuts across them, which is exactly why a bar
    encloses a lagoon), and step it seaward. Hand-placing this put the spit 400
    to 800 m out in deep water the moment the terrain moved, and it would do so
    again every time the generator is retuned.
    """
    S = C.SPIT
    land = h > 0.0
    gh, gw = h.shape
    xs, zs = [], []
    x0 = int((S['x_from'] - C.WORLD_MIN_X) / C.CELL)
    x1 = int((S['x_to'] - C.WORLD_MIN_X) / C.CELL)
    zlim = int((S['search_from_z'] - C.WORLD_MIN_Z) / C.CELL)
    for col in range(max(0, x0), min(gw, x1), 8):
        rows = np.nonzero(land[zlim:, col])[0]
        if rows.size == 0:
            continue
        # The southernmost land in this column is the open-coast shoreline.
        zc = (rows.max() + zlim) * C.CELL + C.WORLD_MIN_Z
        xs.append(col * C.CELL + C.WORLD_MIN_X)
        zs.append(zc)
    if len(xs) < 8:
        return None
    xs = np.asarray(xs, dtype=np.float64)
    zs = gaussian_filter(np.asarray(zs, dtype=np.float64), S['smooth'])
    # Step seaward, growing with distance along the drift, and hook at the end
    # where the drift runs out of energy.
    tt = np.linspace(0.0, 1.0, len(xs))
    off = S['offshore'] * (0.45 + 0.55 * tt) + S['hook'] * np.clip(tt - 0.82, 0, 1) * 5.0
    return list(zip(xs.tolist(), (zs + off).tolist()))


def deposit(h, wx, wz):
    h = h.copy()

    # The barrier spit. Longshore drift piles sand into a ridge that runs with
    # the drift and hooks where it runs out of energy.
    S = C.SPIT
    line = _drift_line(h, wx, wz)
    if line is None:
        return h
    d, t = _line_fields(line, wx, wz)
    across = np.clip(d / S['half_width'], 0.0, 1.0)
    # Asymmetric section: steep on the ocean face, a long shallow back-slope
    # into the lagoon, which is what a real spit looks like in section.
    prof = (1.0 - across ** 2) ** 1.3
    dunes = fbm(wx / 55.0, wz / 55.0, C.SEED + 811, octaves=4) * S['dune_amp']
    ridge = S['crest'] * prof * (1.0 - 0.28 * t) + dunes * prof
    # Sand only piles up where there is a bed shallow enough to pile it on; in
    # deep water the drift carries straight past.
    buildable = smoothstep(-14.0, -5.0, h)
    ridge = ridge * buildable
    # Gate on the ridge actually HAVING height, not on being near the line. A
    # proximity band floors its whole corridor to the offset depth and puts
    # radial caps at the ends of the line, which came out as two rounded lobes
    # of shallow water reaching into the open sea.
    h = np.where(ridge > 0.05, np.maximum(h, ridge), h)

    # Behind the bar the water is cut off from the swell and silts up: a lagoon
    # is shallow BECAUSE the bar is there, so it is derived from the bar rather
    # than drawn as its own polygon.
    line_z = np.interp(wx, [p[0] for p in line], [p[1] for p in line])
    # A strip between the bar and the shore, not a radius around the bar — a
    # radius makes discs at the ends of the line and the lagoon comes out as a
    # pair of rounded lobes reaching out into the open sea.
    # Feather the ends so the lagoon does not stop at a straight line in x.
    ends = (smoothstep(S['x_from'] - 40.0, S['x_from'] + 260.0, wx)
            * (1.0 - smoothstep(S['x_to'] - 320.0, S['x_to'], wx)))
    inshore = (wz < line_z) & (wz > line_z - S['offshore'] - 300.0) & (h < 0.0) & (ends > 0.02)
    near = smoothstep(S['offshore'] + 300.0, S['half_width'], np.abs(wz - line_z)) * ends
    h = np.where(inshore, np.maximum(h, C.LAGOON_DEPTH * near + h * (1.0 - near)), h)

    # The river drops its load where it meets still water.
    D = C.DELTA
    dd = np.hypot(wx - D['c'][0], wz - D['c'][1])
    silt = D['amount'] * np.clip(1.0 - dd / D['r'], 0.0, 1.0) ** 1.5
    h = h + silt * (h < 2.0)

    return h


# ---------------------------------------------------------------------------
# 6  human works
# ---------------------------------------------------------------------------
def human_works(h, wx, wz):
    """Made ground, cut platforms and the quarry.

    Reclaimed land gets a hard edge because it has a seawall — a made-ground
    waterfront meets the water as a vertical face, not as a beach, and that
    single detail is most of what makes a port read as a port."""
    h = h.copy()

    for r in C.RECLAIM:
        m = _poly_mask(r['poly'], wx, wz, blur=1.2, jitter=9.0, seed=hash(r['name']) % 9973)
        # Nobody fills deep water and nobody flattens a hill to make a wharf.
        # Gating on the ground that is actually there means a polygon that
        # overshoots costs nothing, instead of stamping a plateau across the
        # harbour — which is a rule that cannot go wrong rather than a polygon
        # that has to be redrawn every time the coast moves.
        fillable = smoothstep(-11.0, -7.0, h) * (1.0 - smoothstep(r['height'] + 1.5,
                                                                  r['height'] + 7.0, h))
        m = m * fillable
        settle = fbm(wx / 150.0, wz / 150.0, C.SEED + 733, octaves=3) * 0.28
        h = h * (1.0 - m) + (r['height'] + settle) * m

    q = C.QUARRY
    # A quarry is a bite out of a hillside, so it only exists where there is one.
    qm = _poly_mask(q['poly'], wx, wz, blur=2.5, jitter=14.0, seed=451) * smoothstep(8.0, 22.0, h)
    # Benches: step down from the rim towards the floor, following the polygon.
    inner = distance_transform_edt(qm > 0.5) * C.CELL
    steps = np.floor(inner / q['bench_w'])
    pit = np.maximum(q['floor'], h - steps * q['bench_h'])
    h = np.where(qm > 0.5, np.minimum(h, pit), h)

    return h


# ---------------------------------------------------------------------------
def build(stage=3):
    t0 = time.time()
    wx, wz = world_grid()

    u = uplift(wx, wz)
    h = u + relief(wx, wz, u)
    print(f'  uplift + relief     {time.time()-t0:5.1f}s   {h.min():7.1f} … {h.max():6.1f} m')

    h = carve_valley(h, wx, wz)
    print(f'  valley              {time.time()-t0:5.1f}s   {h.min():7.1f} … {h.max():6.1f} m')

    # Erode on the coarse grid.
    t1 = time.time()
    ez, ex = C.EROSION_H, C.EROSION_W
    small = np.asarray(Image.fromarray(h).resize((ex, ez), Image.BILINEAR))
    eroded_small = erode(small, C.EROSION_CELL)
    up = np.asarray(Image.fromarray(eroded_small).resize((C.GRID_W, C.GRID_H), Image.BICUBIC))
    removed = np.asarray(Image.fromarray((small - eroded_small).astype(np.float32))
                         .resize((C.GRID_W, C.GRID_H), Image.BICUBIC))
    # Keep the sub-8 m detail, but not inside the channels erosion just cut —
    # otherwise the fine noise fills the valleys straight back in.
    detail = (h - gaussian_filter(h, 3.0)) * np.clip(1.0 - removed / 9.0, 0.12, 1.0)
    h = (up + detail).astype(np.float32)
    print(f'  erosion {C.EROSION_ITERS:>3} iters  {time.time()-t1:5.1f}s   '
          f'{h.min():7.1f} … {h.max():6.1f} m')

    if stage >= 2:
        h = deposit(h, wx, wz)
    if stage >= 3:
        h = human_works(h, wx, wz)
    print(f'  deposition + works  {time.time()-t0:5.1f}s   {h.min():7.1f} … {h.max():6.1f} m')

    return h.astype(np.float32), wx, wz


# ---------------------------------------------------------------------------
# the flood, and what it leaves behind
# ---------------------------------------------------------------------------
def flood(h, min_island_m2=900.0):
    """Sea level meets the surface. Everything below zero is water.

    Speckle — single cells poking above the water — is not an island, it is a
    generator artefact, so anything too small to stand on is removed."""
    land = h > C.SEA_LEVEL
    land = remove_small_objects(land, int(min_island_m2 / (C.CELL * C.CELL)))
    # Likewise a one-cell puddle inland is not a lake.
    holes = binary_fill_holes(land) & ~land
    holes = remove_small_objects(holes, int(600.0 / (C.CELL * C.CELL)))
    land = binary_fill_holes(land) & ~holes
    return land


def signed_distance(land, cell=None):
    cell = cell or C.CELL
    d_out = distance_transform_edt(~land) * cell
    d_in = distance_transform_edt(land) * cell
    return (d_in - d_out).astype(np.float32)
