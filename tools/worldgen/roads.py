"""The road network.

Roads are not drawn here. They are **routed**, over a cost surface built from the
finished terrain, in the order the real ones were built — because that order is
why a city's network looks the way it does. The shore road came first, because
the wharves came first, and everything since has had to work around it.

The mechanism is least-cost path routing, which is what a highway engineer
actually does: gradient is expensive, water is very expensive, and an existing
corridor is cheap because it is already cut, already drained and already owned.
Run it in historical order with the cost surface updated after each route and
the network comes out sharing corridors, converging on crossings, and bending
around the things that were in the way — none of which anyone placed.

    python3 -m tools.worldgen.roads --preview
"""
import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt
from scipy.interpolate import splprep, splev
from skimage.graph import route_through_array

from . import config as C


# Routing runs coarser than the heightfield. A 2 m grid is 5 M nodes and buys
# nothing: a road's alignment is decided at the scale of tens of metres, and the
# path gets splined afterwards anyway.
R_CELL = 8.0


def _downsample(a, cell=R_CELL):
    k = int(cell / C.CELL)
    h, w = a.shape
    return a[:h // k * k, :w // k * k].reshape(h // k, k, w // k, k).mean(axis=(1, 3))


def to_grid(x, z, cell=R_CELL):
    return (int(round((z - C.WORLD_MIN_Z) / cell)), int(round((x - C.WORLD_MIN_X) / cell)))


def to_world(r, c, cell=R_CELL):
    return (c * cell + C.WORLD_MIN_X, r * cell + C.WORLD_MIN_Z)


def cost_surface(h, land):
    """What it costs to put a metre of road here.

    Gradient dominates, and it dominates non-linearly: a 4% grade is a road, a
    12% grade is an expensive road, and past about 20% nothing wheeled goes up
    it at all, so the penalty has to rise fast enough that the router prefers a
    long way round — which is exactly how switchbacks get invented rather than
    placed.
    """
    hs = _downsample(h)
    ls = _downsample(land.astype(np.float32)) > 0.5

    gz, gx = np.gradient(gaussian_filter(hs, 1.0), R_CELL)
    grade = np.hypot(gx, gz)

    cost = np.ones_like(hs, dtype=np.float64)
    cost += (grade / 0.04) ** 2.6 * 0.9          # gradient, rising hard
    # Very low ground floods and needs raising; very close to the water needs a wall.
    cost += np.clip(2.5 - hs, 0, None) * 0.8 * ls
    cost[~ls] = 4000.0                            # water: crossable only by bridge
    # Keep off the very edge of the world.
    cost[:2, :] = cost[-2:, :] = cost[:, :2] = cost[:, -2:] = 1e6
    return cost, hs, ls


def route(cost, a, b):
    """One least-cost path between two world positions."""
    ra, rb = to_grid(*a), to_grid(*b)
    hgt, wid = cost.shape
    ra = (int(np.clip(ra[0], 0, hgt - 1)), int(np.clip(ra[1], 0, wid - 1)))
    rb = (int(np.clip(rb[0], 0, hgt - 1)), int(np.clip(rb[1], 0, wid - 1)))
    path, _ = route_through_array(cost, ra, rb, fully_connected=True, geometric=True)
    return np.asarray(path)


def discount(cost, path, factor=0.22, width=2):
    """An existing corridor is cheap to build alongside — it is already cut,
    drained and owned. Applying this after each route is what makes roads share
    alignments and converge on crossings instead of each finding its own way."""
    mask = np.zeros(cost.shape, bool)
    for (r, c) in path:
        r0, r1 = max(0, r - width), min(cost.shape[0], r + width + 1)
        c0, c1 = max(0, c - width), min(cost.shape[1], c + width + 1)
        mask[r0:r1, c0:c1] = True
    cost[mask] = np.maximum(1.0, cost[mask] * factor)
    return cost


def smooth_path(path, cell=R_CELL, smoothing=None):
    """Grid path → smooth centreline.

    A road is a spline with camber and superelevation, not a polyline of
    straight quads with hard corners. Faceted curves are one of the loudest
    generated-geometry tells there is, and roads and kerbs are the longest
    curves in a city.
    """
    pts = np.array([to_world(r, c, cell) for (r, c) in path], dtype=np.float64)
    if len(pts) < 6:
        return pts
    # Drop near-duplicates, which make splprep singular.
    keep = [0]
    for i in range(1, len(pts)):
        if np.hypot(*(pts[i] - pts[keep[-1]])) > cell * 0.6:
            keep.append(i)
    pts = pts[keep]
    if len(pts) < 6:
        return pts
    # Light smoothing only. At s = len·24 the spline pulled so far off the
    # least-cost path that roads left the corridor they had just paid to find
    # and ran over cliffs and across water — a 446% grade on Bar Road, 8% of it
    # in the lagoon. The routing knows where the road goes; smoothing is only
    # allowed to take the staircase off it.
    s = smoothing if smoothing is not None else len(pts) * 1.8
    tck, _ = splprep([pts[:, 0], pts[:, 1]], s=s, k=3)
    u = np.linspace(0, 1, max(24, int(len(pts) * 2.2)))
    sx, sy = splev(u, tck)
    return np.column_stack([sx, sy])


# ---------------------------------------------------------------------------
# Where a crossing goes is not a decision — it is a measurement
# ---------------------------------------------------------------------------
def find_narrows(ls, x_from, x_to, z_from, z_to):
    """The shortest water span across the harbour in a given stretch.

    Bridges are not where somebody liked them. They are where the water is
    narrowest and the banks are firm, because that is what is affordable — and
    the ferry was there for the same reason a century earlier. So it is found
    from the terrain rather than written down, and it moves when the terrain
    moves.

    Measured as the shortest CONTIGUOUS run of water with land immediately on
    both sides. Taking the column's min-to-max water extent instead rejects any
    crossing whose water touches the edge of the search window, which is why the
    Causeway — where the far bank is a thin spit with open sea beyond it — could
    not be found at all.
    """
    best = None
    c0, c1 = int((x_from - C.WORLD_MIN_X) / R_CELL), int((x_to - C.WORLD_MIN_X) / R_CELL)
    r0, r1 = int((z_from - C.WORLD_MIN_Z) / R_CELL), int((z_to - C.WORLD_MIN_Z) / R_CELL)
    r0, r1 = max(0, r0), min(ls.shape[0], r1)
    for c in range(max(0, c0), min(ls.shape[1], c1)):
        col = ls[r0:r1, c]
        i = 0
        n = col.size
        while i < n:
            if col[i]:
                i += 1
                continue
            j = i
            while j < n and not col[j]:
                j += 1
            # Land on both sides of this run, and both banks inside the window.
            if i > 0 and j < n:
                span = (j - i) * R_CELL
                if span >= 60.0 and (best is None or span < best[0]):
                    best = (span, to_world(r0 + i - 1, c), to_world(r0 + j, c))
            i = j + 1
    return best


def stamp_bridge(cost, a, b, price=22.0, width=1):
    """A crossing corridor the router may use. Priced high enough that it only
    gets used where a bridge is genuinely worth it, and low enough that it is
    cheaper than driving round the head of the harbour."""
    ra, rb = to_grid(*a), to_grid(*b)
    n = int(max(abs(rb[0] - ra[0]), abs(rb[1] - ra[1]))) + 1
    for i in range(n + 1):
        t = i / max(1, n)
        r = int(round(ra[0] + (rb[0] - ra[0]) * t))
        c = int(round(ra[1] + (rb[1] - ra[1]) * t))
        r0, r1 = max(0, r - width), min(cost.shape[0], r + width + 1)
        c0, c1 = max(0, c - width), min(cost.shape[1], c + width + 1)
        cost[r0:r1, c0:c1] = np.minimum(cost[r0:r1, c0:c1], price)
    return cost


def snap_to_land(x, z, hs, ls, want_gentle=True, radius=40):
    """Move a waypoint to the nearest ground a road could actually start on.

    Waypoints are written against a plan; the terrain is generated. Snapping
    means a district centre that lands in the water or on a cliff costs nothing
    instead of producing a road into the sea."""
    r, c = to_grid(x, z)
    best, bestd = None, 1e18
    gz, gx = np.gradient(hs, R_CELL)
    grade = np.hypot(gx, gz)
    for dr in range(-radius, radius + 1):
        for dc in range(-radius, radius + 1):
            rr, cc = r + dr, c + dc
            if not (0 <= rr < ls.shape[0] and 0 <= cc < ls.shape[1]):
                continue
            if not ls[rr, cc] or hs[rr, cc] < 0.6:
                continue
            if want_gentle and grade[rr, cc] > 0.16:
                continue
            d = dr * dr + dc * dc
            if d < bestd:
                bestd, best = d, (rr, cc)
    return to_world(*best) if best is not None else None


# ---------------------------------------------------------------------------
# What gets routed, in the order it was built
# ---------------------------------------------------------------------------
def build(h, land, verbose=True):
    cost, hs, ls = cost_surface(h, land)
    net = []
    crossings = {}

    for b in C.BRIDGES:
        found = find_narrows(ls, *b['search'])
        if found is None:
            if verbose:
                print(f"  ! no crossing found for {b['name']}")
            continue
        span, north, south = found
        crossings[b['key']] = dict(name=b['name'], span=span, north=north, south=south)
        stamp_bridge(cost, north, south, b['price'])
        if verbose:
            print(f"  {b['name']}: narrowest span {span:.0f} m "
                  f"at x={north[0]:.0f}  ({north[1]:.0f} → {south[1]:.0f})")

    def add(name, cls, waypoints, discount_factor=0.22):
        snapped = []
        for (x, z) in waypoints:
            p = snap_to_land(x, z, hs, ls)
            # A waypoint with no reachable land near it is DROPPED, not routed
            # to. Routing to it anyway is how Bar Road ended up running off the
            # bottom of the map with 8% of its length in the sea.
            if p is not None:
                snapped.append(p)
        waypoints = snapped
        if len(waypoints) < 2:
            if verbose:
                print(f'  ! {name}: too few reachable waypoints, skipped')
            return None
        full = []
        for i in range(len(waypoints) - 1):
            p = route(cost, waypoints[i], waypoints[i + 1])
            full.append(p if i == 0 else p[1:])
        path = np.vstack(full)
        line = smooth_path(path)
        net.append(dict(name=name, cls=cls, path=line))
        discount(cost, path, discount_factor)
        return line

    for spec in C.ROADS:
        add(spec['name'], spec['cls'], spec['via'], spec.get('discount', 0.22))

    return net, cost, hs, ls


def grade_report(net, h):
    """Every generated road, checked as data before anything is built from it.

    A gradient nothing can climb is invisible in a plan view and fatal in a car,
    so it gets measured here rather than discovered by driving into it.
    """
    rows = []
    for r in net:
        p = r['path']
        if len(p) < 2:
            rows.append((r['name'], 0.0, 0.0, 0.0, 'EMPTY'))
            continue
        ix = np.clip(((p[:, 0] - C.WORLD_MIN_X) / C.CELL).astype(int), 0, C.GRID_W - 1)
        iz = np.clip(((p[:, 1] - C.WORLD_MIN_Z) / C.CELL).astype(int), 0, C.GRID_H - 1)
        elev = h[iz, ix]
        seg = np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1]))
        # Gradient over a chord a vehicle actually spans, not between adjacent
        # samples: a single-cell spike in a 2 m heightfield is not a hill, and
        # per-sample differencing reports it as a cliff.
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        chord = 16.0
        gi = np.searchsorted(cum, cum + chord).clip(0, len(cum) - 1)
        run = np.maximum(cum[gi] - cum, 1e-3)
        grade = np.abs(elev[gi] - elev) / run * 100.0
        grade = grade[run > chord * 0.4]
        if grade.size == 0:
            grade = np.zeros(1)
        length = seg.sum()
        below = (elev < 0.2).mean()
        flag = ''
        if grade.max() > 18:
            flag = f'MAX GRADE {grade.max():.0f}%'
        if below > 0.02:
            flag = (flag + ' ') + f'{below*100:.0f}% IN WATER'
        rows.append((r['name'], length, float(np.percentile(grade, 95)), float(grade.max()), flag))
    return rows


# ---------------------------------------------------------------------------
def main():
    import argparse, os, time
    import numpy as np
    from . import preview

    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--tag', default='')
    args = ap.parse_args()

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    cache = os.path.join(root, '.worldcache')
    h = np.load(os.path.join(cache, 'height.npy'))
    land = np.load(os.path.join(cache, 'land.npy'))

    t0 = time.time()
    print('routing…')
    net, cost, hs, ls = build(h, land)
    print(f'  {len(net)} roads in {time.time()-t0:.1f}s')

    np.savez(os.path.join(cache, 'roads.npz'),
             **{r['name'].replace(' ', '_'): r['path'] for r in net})

    print()
    print(f'  {"road":<26} {"length":>8}  {"p95":>5} {"max":>5}   check')
    total = 0.0
    for (name, length, p95, mx, flag) in grade_report(net, h):
        total += length
        print(f'  {name:<26} {length:7.0f} m  {p95:4.1f}% {mx:4.1f}%   {flag}')
    print(f'  {"TOTAL":<26} {total/1000:7.2f} km')

    if args.preview:
        out = os.path.join(root, 'shots', 'world', f'roads{args.tag}.png')
        print('\n  ' + os.path.relpath(preview.aerial_with_roads(h, land, net, out=out), root))


if __name__ == '__main__':
    main()
