#!/usr/bin/env python3
"""Look at many things at once, because a fault you cannot see alone is obvious in a row.

Contact sheet — capture a set of named views and tile them into one labelled image:

    ~/imagegen/bin/python tools/sheet.py --url http://127.0.0.1:8080 --views views.json -o sheet.png

    views.json = [
      {"name": "downtown noon",  "eval": "game.goto('downtown'); game.setHour(12)"},
      {"name": "downtown dusk",  "eval": "game.goto('downtown'); game.setHour(19.5)"},
      {"name": "docks noon",     "eval": "game.goto('docks');    game.setHour(12)"}
    ]

Pair — put two images side by side with a difference readout, optionally blind:

    ~/imagegen/bin/python tools/sheet.py --pair before.png after.png -o compare.png
    ~/imagegen/bin/python tools/sheet.py --pair mine.png reference.jpg -o gap.png
    ~/imagegen/bin/python tools/sheet.py --pair mine.png reference.jpg -o gap.png --blind

Why this exists rather than a folder of separate captures: the two failures the brief cares most
about are only visible in comparison. "If you cannot tell which district each shot came from" is a
judgement you cannot make one image at a time, and neither is "does this look like the photograph".
A row makes both instant.

The pair mode prints mean absolute difference and a per-channel mean for each image. Treat those as
a hint about *where* to look, never as the judgement — a frame can score closer and read worse. Your
eyes are the instrument; this is the lens.
"""
import argparse, json, pathlib, sys

GPU_ARGS = ["--enable-unsafe-webgpu", "--use-angle=metal", "--enable-features=Vulkan,WebGPU",
            "--ignore-gpu-blocklist"]


def label(img, text, height=28):
    from PIL import Image, ImageDraw
    out = Image.new("RGB", (img.width, img.height + height), (16, 17, 22))
    out.paste(img, (0, height))
    d = ImageDraw.Draw(out)
    d.text((8, height // 2 - 6), text[:120], fill=(220, 222, 230))
    return out


def tile(images, cols):
    from PIL import Image
    if not images:
        sys.exit("nothing captured")
    w = max(i.width for i in images)
    h = max(i.height for i in images)
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, h * rows), (16, 17, 22))
    for n, im in enumerate(images):
        sheet.paste(im, ((n % cols) * w, (n // cols) * h))
    return sheet


def do_pair(a_path, b_path, out, blind=False):
    from PIL import Image
    import numpy as np
    a = Image.open(a_path).convert("RGB")
    b = Image.open(b_path).convert("RGB")
    h = min(a.height, b.height)
    a = a.resize((int(a.width * h / a.height), h))
    b = b.resize((int(b.width * h / b.height), h))
    if blind:
        import random
        pair = [(a, a_path), (b, b_path)]
        random.shuffle(pair)
        sheet = tile([label(pair[0][0], "A"), label(pair[1][0], "B")], 2)
        key = {"A": pathlib.Path(pair[0][1]).name, "B": pathlib.Path(pair[1][1]).name}
    else:
        sheet = tile([label(a, pathlib.Path(a_path).name), label(b, pathlib.Path(b_path).name)], 2)
        key = None
    sheet.save(out)
    sa, sb = np.asarray(a.resize(b.size), dtype=float), np.asarray(b, dtype=float)
    print(f"wrote {out}")
    if key:
        print(f"  BLIND: labelled A and B in random order. Key: {key}")
        print("  Give the image to the critic. Do not give it the key, and do not tell it which")
        print("  one you made — a critic that knows will find reasons to prefer yours.")
    print(f"  mean abs difference: {abs(sa - sb).mean():.1f} / 255")
    for i, ch in enumerate("RGB"):
        print(f"  mean {ch}: {sa[..., i].mean():6.1f}  vs {sb[..., i].mean():6.1f}")
    print("  A number moving the right way is not evidence the frame improved. Look at both.")


def do_sheet(url, views, out, w, h, wait, cols):
    from playwright.sync_api import sync_playwright
    from PIL import Image
    import io
    images, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=GPU_ARGS)
        page = browser.new_page(viewport={"width": w, "height": h})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(url, wait_until="load", timeout=60000)
        page.wait_for_timeout(wait)
        for v in views:
            js = v.get("eval")
            if js:
                try:
                    page.evaluate(js)
                except Exception as e:
                    errors.append(f"{v.get('name')}: {e}")
            page.wait_for_timeout(v.get("wait", wait))
            images.append(label(Image.open(io.BytesIO(page.screenshot())), v.get("name", "?")))
            print(f"  captured {v.get('name')}")
        browser.close()
    tile(images, cols).save(out)
    print(f"wrote {out}  ({len(images)} views)")
    for e in errors[:10]:
        print("  page error:", e)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    ap.add_argument("--views", help="JSON file: [{name, eval, wait}]")
    ap.add_argument("--pair", nargs=2, metavar=("A", "B"))
    ap.add_argument("-o", "--out", default="sheet.png")
    ap.add_argument("--w", type=int, default=800)
    ap.add_argument("--h", type=int, default=500)
    ap.add_argument("--wait", type=int, default=1500)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--blind", action="store_true",
                    help="pair mode: label A/B in random order and print the key separately")
    a = ap.parse_args()

    if a.pair:
        do_pair(a.pair[0], a.pair[1], a.out, blind=a.blind)
    elif a.url and a.views:
        do_sheet(a.url, json.loads(pathlib.Path(a.views).read_text()), a.out, a.w, a.h, a.wait, a.cols)
    else:
        ap.error("need --pair A B, or --url with --views")
