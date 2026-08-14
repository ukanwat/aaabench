"""Build the world.

    python3 -m tools.worldgen.build --preview

The generator is authoritative over its output. Nothing downstream is hand-edited:
if the world is wrong, the rule that made it is wrong.
"""
import argparse
import os
import time

import numpy as np

from . import config as C
from . import terrain, preview

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, '.worldcache')
SHOTS = os.path.join(ROOT, 'shots', 'world')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true')
    ap.add_argument('--erosion', type=int, default=None, help='override iteration count')
    ap.add_argument('--tag', default='', help='suffix for the preview filenames')
    ap.add_argument('--stage', type=int, default=3,
                    help='1 natural terrain only · 2 + deposition · 3 + human works')
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(SHOTS, exist_ok=True)
    if args.erosion is not None:
        C.EROSION_ITERS = args.erosion

    t0 = time.time()
    print(f'Ashmouth — {C.WORLD_W:.0f} × {C.WORLD_H:.0f} m at {C.CELL:.0f} m/cell '
          f'({C.GRID_W}×{C.GRID_H})')

    h, wx, wz = terrain.build(stage=args.stage)
    land = terrain.flood(h)
    # Anything the flood rejected as too small to be an island is put back under
    # the water, so the height field and the land mask never disagree.
    h = np.where(land, np.maximum(h, 0.05), np.minimum(h, -0.05)).astype(np.float32)
    sdf = terrain.signed_distance(land)

    np.save(os.path.join(CACHE, 'height.npy'), h)
    np.save(os.path.join(CACHE, 'land.npy'), land)
    np.save(os.path.join(CACHE, 'sdf.npy'), sdf)

    print()
    print(preview.stats(h, land))
    print()

    if args.preview:
        t = args.tag
        print('renders…')
        for p in (
            preview.aerial(h, land, out=os.path.join(SHOTS, f'aerial{t}.png')),
            preview.slope_map(h, land, out=os.path.join(SHOTS, f'slope{t}.png')),
            preview.section(h, -60, out=os.path.join(SHOTS, f'section-narrows{t}.png')),
            preview.section(h, 520, out=os.path.join(SHOTS, f'section-bellcross{t}.png')),
        ):
            print('  ' + os.path.relpath(p, ROOT))

    print(f'done in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
