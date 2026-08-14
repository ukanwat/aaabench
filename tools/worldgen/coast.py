"""The coastline.

Hand-drawn control polygons become smooth closed splines, then get roughened by
noise that is periodic around the loop (so there is no seam where the curve
closes), then get re-splined so the result is a genuine curve rather than a
polyline of straight quads. Coastlines are the longest curves in the world and
faceting on them is one of the loudest generated-geometry tells there is.

Roughness is per-landmass and physical: sand smooths a coast out, rock does the
opposite. Tern Bar is a drift-built spit and is nearly smooth; North Point is
rock and is deeply indented.
"""
import numpy as np
from scipy.interpolate import splprep, splev
from scipy.ndimage import distance_transform_edt
from PIL import Image, ImageDraw

from . import config as C
from .noisefield import perlin


def _resample_closed(points, n):
    """Periodic cubic spline through the control points, sampled n times."""
    pts = np.asarray(points, dtype=np.float64)
    x, y = pts[:, 0], pts[:, 1]
    # splprep with per=1 wants the loop open; it closes it itself.
    tck, _ = splprep([x, y], s=0, per=1, k=3)
    u = np.linspace(0.0, 1.0, n, endpoint=False)
    sx, sy = splev(u, tck)
    return np.stack([sx, sy], axis=1)


def _outward_normals(curve):
    """Unit normals pointing away from the centroid, so a positive displacement
    always grows the landmass."""
    nxt = np.roll(curve, -1, axis=0)
    prv = np.roll(curve, 1, axis=0)
    tang = nxt - prv
    tang /= np.maximum(1e-9, np.linalg.norm(tang, axis=1, keepdims=True))
    nrm = np.stack([-tang[:, 1], tang[:, 0]], axis=1)
    centroid = curve.mean(axis=0)
    facing = np.einsum('ij,ij->i', nrm, curve - centroid)
    nrm[facing < 0] *= -1.0
    return nrm


def _periodic_noise(n, seed, octaves):
    """Noise around a loop. Sampling a circle in 2D noise is periodic by
    construction — no seam, no tapering hack at the join.

    `octaves` is a list of (wavelength_in_loop_fractions, amplitude_m).
    """
    theta = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    out = np.zeros(n, dtype=np.float32)
    for i, (cycles, amp) in enumerate(octaves):
        r = cycles / (2.0 * np.pi)
        cx = np.cos(theta) * r
        cy = np.sin(theta) * r
        out += perlin(cx.astype(np.float32), cy.astype(np.float32), seed + i * 4517) * amp
    return out


def build_outline(poly, rough=1.0, seed=0, samples=2400):
    """Control polygon → smooth, roughened, re-splined closed coastline."""
    base = _resample_closed(poly, samples)
    nrm = _outward_normals(base)

    # Three scales of coastal irregularity, in metres of displacement:
    # bays and headlands, coves, and the metre-scale ragged edge.
    disp = _periodic_noise(samples, seed, [
        (3.0,  62.0 * rough),    # bays / headlands
        (9.0,  24.0 * rough),    # coves
        (23.0,  9.0 * rough),    # inlets and points
        (61.0,  3.2 * rough),    # ragged edge
    ])
    rough_curve = base + nrm * disp[:, None]

    # Re-spline so the roughened outline is smooth again at the sample scale.
    # Without this the noise leaves visible kinks and the shore reads as faceted.
    return _resample_closed(rough_curve, samples * 2)


def rasterise(curve, grid_w, grid_h, cell, min_x, min_z, supersample=3):
    """Closed curve → boolean land mask, supersampled so the edge is honest."""
    sw, sh = grid_w * supersample, grid_h * supersample
    img = Image.new('L', (sw, sh), 0)
    px = (curve[:, 0] - min_x) / cell * supersample
    pz = (curve[:, 1] - min_z) / cell * supersample
    ImageDraw.Draw(img).polygon(list(zip(px.tolist(), pz.tolist())), fill=255)
    small = img.resize((grid_w, grid_h), Image.LANCZOS)
    return np.asarray(small, dtype=np.float32) / 255.0


def signed_distance(coverage, cell):
    """Signed distance to the coast in metres: positive on land, negative in
    water. Built from the antialiased coverage so the shoreline sits at 0.5
    rather than on a pixel boundary."""
    land = coverage >= 0.5
    d_out = distance_transform_edt(~land) * cell
    d_in = distance_transform_edt(land) * cell
    return (d_in - d_out).astype(np.float32)


def polyline_distance(pts, grid_w, grid_h, cell, min_x, min_z, samples=1200):
    """Distance in metres from every cell to a (splined) open polyline. Used for
    the Sound's thalweg and the river — both are lines the terrain has to know
    about."""
    p = np.asarray(pts, dtype=np.float64)
    tck, _ = splprep([p[:, 0], p[:, 1]], s=0, k=min(3, len(p) - 1))
    u = np.linspace(0, 1, samples)
    sx, sy = splev(u, tck)

    img = Image.new('L', (grid_w, grid_h), 0)
    px = (np.asarray(sx) - min_x) / cell
    pz = (np.asarray(sy) - min_z) / cell
    ImageDraw.Draw(img).line(list(zip(px.tolist(), pz.tolist())), fill=255, width=1)
    on_line = np.asarray(img) > 0
    if not on_line.any():
        return np.full((grid_h, grid_w), 1e6, dtype=np.float32), np.zeros((grid_h, grid_w), np.float32)

    dist, idx = distance_transform_edt(~on_line, return_indices=True)

    # Also carry "how far along the line" so depth/width can vary down its length.
    t_img = np.zeros((grid_h, grid_w), dtype=np.float32)
    ix = np.clip(px.astype(int), 0, grid_w - 1)
    iz = np.clip(pz.astype(int), 0, grid_h - 1)
    t_img[iz, ix] = u.astype(np.float32)
    along = t_img[idx[0], idx[1]]
    return (dist * cell).astype(np.float32), along


def build():
    """All the coast-derived fields, on the master grid."""
    gw, gh, cell = C.GRID_W, C.GRID_H, C.CELL
    mnx, mnz = C.WORLD_MIN_X, C.WORLD_MIN_Z

    outlines, coverages = {}, {}
    total = np.zeros((gh, gw), dtype=np.float32)
    for key, spec in C.LANDMASSES.items():
        curve = build_outline(spec['poly'], spec['rough'], C.SEED + spec['seed'])
        cov = rasterise(curve, gw, gh, cell, mnx, mnz)
        outlines[key] = curve
        coverages[key] = cov
        total = np.maximum(total, cov)

    # Islets are small enough to be discs with a little noise on them.
    yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
    wx = xx * cell + mnx
    wz = yy * cell + mnz
    for i, (cx, cz, r, _h) in enumerate(C.ISLETS):
        d = np.hypot(wx - cx, wz - cz)
        wobble = perlin((wx - cx) / 40.0, (wz - cz) / 40.0, C.SEED + 900 + i) * (r * 0.22)
        total = np.maximum(total, (d < (r + wobble)).astype(np.float32))

    sdf = signed_distance(total, cell)
    sound_d, sound_t = polyline_distance(C.SOUND_CHANNEL, gw, gh, cell, mnx, mnz)
    river_d, river_t = polyline_distance(C.RIVER_ASH, gw, gh, cell, mnx, mnz)

    return dict(
        outlines=outlines, coverage=total, land=total >= 0.5, sdf=sdf,
        sound_d=sound_d, sound_t=sound_t,
        river_d=river_d, river_t=river_t,
        wx=wx, wz=wz,
    )
