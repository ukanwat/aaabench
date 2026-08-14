#!/usr/bin/env python3
"""Compare two shot sets pixel by pixel, and say exactly what moved.

    python3 tools/imagediff.py --a shots/base --b shots/after
    python3 tools/imagediff.py --a shots/base --b shots/after --tol 2 --write-diff

The gate this exists for: **an optimisation that changes the picture is not an optimisation.**
Shoot a fixed set with `baseline.py`, do the performance work, shoot the same set, diff them.
Every pixel that moved is either a bug you just wrote or a trade you are making on purpose — and
if it is on purpose, the number belongs in `PROGRESS.md` next to the milliseconds you bought
with it.

Also useful across sessions: the same set re-shot each time catches the slow drift that no single
change is responsible for.

`--tol` is the per-channel 0–255 delta below which a pixel counts as unchanged; 1–2 absorbs
dithering and temporal jitter without hiding real change. Exits non-zero if anything moved beyond
it, so it can gate a script.

It refuses to compare sets taken on different renderers or viewports, because that is not a
comparison and the numbers would look like a regression.
"""
import argparse, json, pathlib, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="baseline directory")
    ap.add_argument("--b", required=True, help="directory to compare against it")
    ap.add_argument("--tol", type=int, default=0, help="per-channel delta counted as unchanged")
    ap.add_argument("--write-diff", action="store_true", help="write <name>.diff.png heatmaps into --b")
    a = ap.parse_args()

    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        sys.exit("needs numpy and pillow")

    A, B = pathlib.Path(a.a), pathlib.Path(a.b)
    for d in (A, B):
        if not d.is_dir():
            sys.exit(f"not a directory: {d}")

    # Refuse to compare across renderers — the difference would be the renderer, not the work.
    ma, mb = A / "manifest.json", B / "manifest.json"
    if ma.exists() and mb.exists():
        j1, j2 = json.loads(ma.read_text()), json.loads(mb.read_text())
        if j1.get("renderer") != j2.get("renderer"):
            print(f"!! different renderers — this is not a comparison\n   a: {j1.get('renderer')}\n   b: {j2.get('renderer')}")
            sys.exit(2)
        if j1.get("viewport") != j2.get("viewport"):
            print(f"!! different viewports: {j1.get('viewport')} vs {j2.get('viewport')}")
            sys.exit(2)

    names = sorted(p.name for p in A.glob("*.png") if not p.name.endswith(".diff.png"))
    if not names:
        sys.exit(f"no shots in {A}")

    rows, missing, changed = [], [], 0
    for n in names:
        pb = B / n
        if not pb.exists():
            missing.append(n)
            continue
        ia = np.asarray(Image.open(A / n).convert("RGB"), dtype=np.int16)
        ib = np.asarray(Image.open(pb).convert("RGB"), dtype=np.int16)
        if ia.shape != ib.shape:
            rows.append((n, None, None, f"size {ia.shape[1]}x{ia.shape[0]} vs {ib.shape[1]}x{ib.shape[0]}"))
            changed += 1
            continue
        d = np.abs(ia - ib)
        moved = (d.max(axis=2) > a.tol)
        pct = 100.0 * moved.mean()
        rows.append((n, pct, int(d.max()), None))
        if pct > 0:
            changed += 1
            if a.write_diff:
                heat = np.zeros(ia.shape, dtype=np.uint8)
                heat[..., 0] = np.clip(d.max(axis=2) * 8, 0, 255)
                Image.fromarray(heat).save(B / f"{n[:-4]}.diff.png")

    width = max(len(n) for n, *_ in rows) if rows else 10
    for n, pct, mx, note in rows:
        if note:
            print(f"  {n:<{width}}  {note}")
        elif pct == 0:
            print(f"  {n:<{width}}  identical")
        else:
            print(f"  {n:<{width}}  {pct:6.2f}% of pixels moved, worst channel delta {mx}")

    print()
    if missing:
        print(f"missing from {B}: {', '.join(missing)}")
    print(f"{len(rows) - changed}/{len(rows)} identical within tol={a.tol}")
    if changed:
        print("\nSomething moved. Either it is a defect you just introduced, or it is a trade you\n"
              "made on purpose — in which case write down what you traded and what it bought.")
        sys.exit(1)


if __name__ == "__main__":
    main()
