"""Export the generated world for the runtime.

    python3 -m tools.worldgen.export

The heightfield goes out as one 16-bit raw image rather than as per-chunk
geometry. At 4 m it is 1250 × 1000 × 2 bytes = 2.4 MB, which the GPU can hold as
a single texture, and the terrain is then drawn by displacing a plain grid in
the vertex shader. That means level of detail costs nothing but a coarser grid,
chunks share one source of truth so they cannot disagree at their seams, and
there is no per-chunk mesh data to stream at all.

Centimetre precision over a −655 m … +655 m range is far more than a coastal
city needs, and int16 is exactly what a texture wants.
"""
import json
import os

import numpy as np
from PIL import Image

from . import config as C


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CACHE = os.path.join(ROOT, '.worldcache')
OUT = os.path.join(ROOT, 'workspace', 'world')

EXPORT_CELL = 4.0
HEIGHT_SCALE = 100.0        # metres → int16 centimetres


def main():
    os.makedirs(OUT, exist_ok=True)
    h = np.load(os.path.join(CACHE, 'height.npy'))
    land = np.load(os.path.join(CACHE, 'land.npy'))

    k = int(EXPORT_CELL / C.CELL)
    gh, gw = h.shape
    hs = h[:gh // k * k, :gw // k * k].reshape(gh // k, k, gw // k, k).mean(axis=(1, 3))
    W, H = hs.shape[1], hs.shape[0]

    q = np.clip(np.round(hs * HEIGHT_SCALE), -32768, 32767).astype('<i2')
    q.tofile(os.path.join(OUT, 'height.bin'))

    # A land/water mask at the same resolution, as a single-channel PNG. The
    # shoreline has to be a hard test at render time — a beach is where land
    # meets water, and interpolating across that edge invents a slope nobody
    # can stand on.
    ls = land[:gh // k * k, :gw // k * k].reshape(gh // k, k, gw // k, k).mean(axis=(1, 3))
    Image.fromarray((np.clip(ls, 0, 1) * 255).astype(np.uint8)).save(
        os.path.join(OUT, 'land.png'))

    net = []
    try:
        rd = np.load(os.path.join(CACHE, 'roads.npz'))
        by_name = {r['name'].replace(' ', '_'): r for r in C.ROADS}
        for key in rd.files:
            spec = by_name.get(key, {})
            net.append(dict(
                name=key.replace('_', ' '),
                cls=spec.get('cls', 'secondary'),
                points=[[round(float(x), 2), round(float(z), 2)] for (x, z) in rd[key]],
            ))
    except FileNotFoundError:
        print('  ! no roads.npz — run tools.worldgen.roads first')

    manifest = dict(
        name='Ashmouth',
        bounds=dict(minX=C.WORLD_MIN_X, maxX=C.WORLD_MAX_X,
                    minZ=C.WORLD_MIN_Z, maxZ=C.WORLD_MAX_Z),
        height=dict(file='height.bin', width=W, height=H, cell=EXPORT_CELL,
                    scale=1.0 / HEIGHT_SCALE, format='int16'),
        landMask=dict(file='land.png', width=W, height=H, cell=EXPORT_CELL),
        seaLevel=C.SEA_LEVEL,
        tideRange=C.TIDE_RANGE,
        districts=[dict(key=d['key'], name=d['name'], x=d['c'][0], z=d['c'][1], r=d['r'])
                   for d in C.DISTRICTS],
        roads=net,
        stats=dict(minHeight=float(h.min()), maxHeight=float(h.max()),
                   landAreaKm2=round(float(land.sum()) * C.CELL ** 2 / 1e6, 3)),
    )
    with open(os.path.join(OUT, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=1)

    size = os.path.getsize(os.path.join(OUT, 'height.bin'))
    print(f'  height.bin   {W}×{H} @ {EXPORT_CELL:.0f} m   {size/1e6:.2f} MB')
    print(f'  land.png     {W}×{H}')
    print(f'  manifest     {len(net)} roads, {len(manifest["districts"])} districts, '
          f'{manifest["stats"]["landAreaKm2"]} km² land')


if __name__ == '__main__':
    main()
