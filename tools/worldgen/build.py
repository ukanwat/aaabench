"""Build the world. Entry point:

    python3 -m tools.worldgen.build --preview

The generator is authoritative over its output. Nothing downstream may be
hand-edited: if the world is wrong, the rule that made it is wrong.
"""
import argparse
import os
import time

import numpy as np

from . import config as C
from . import coast, terrain, preview


OUT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'workspace', 'world')
CACHE = os.path.join(os.path.dirname(__file__), '..', '..', '.worldcache')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true', help='write the inspection renders')
    ap.add_argument('--no-erosion', action='store_true')
    ap.add_argument('--out', default=None)
    args = ap.parse_args()

    os.makedirs(CACHE, exist_ok=True)
    shots = os.path.join(os.path.dirname(__file__), '..', '..', 'shots', 'world')
    os.makedirs(shots, exist_ok=True)

    t0 = time.time()
    print(f'Ashmouth — {C.WORLD_W:.0f} × {C.WORLD_H:.0f} m at {C.CELL:.0f} m/cell '
          f'({C.GRID_W}×{C.GRID_H})')

    print('coast…')
    f = coast.build()
    print(f'  {len(f["outlines"])} landmasses, {time.time()-t0:.1f}s')

    print('terrain…')
    if args.no_erosion:
        C.EROSION_ITERS = 0
    h = terrain.build(f)

    np.save(os.path.join(CACHE, 'height.npy'), h)
    np.save(os.path.join(CACHE, 'land.npy'), f['land'])
    np.save(os.path.join(CACHE, 'sdf.npy'), f['sdf'])
    np.savez(os.path.join(CACHE, 'outlines.npz'), **f['outlines'])

    print()
    print(preview.stats(h, f))
    print()

    if args.preview:
        print('renders…')
        print('  ' + preview.aerial(h, out=os.path.join(shots, 'aerial.png')))
        print('  ' + preview.slope_map(h, out=os.path.join(shots, 'slope.png')))
        print('  ' + preview.section(h, -60, out=os.path.join(shots, 'section-narrows.png')))
        print('  ' + preview.section(h, 700, out=os.path.join(shots, 'section-kilnward.png')))

    print(f'done in {time.time()-t0:.1f}s')


if __name__ == '__main__':
    main()
