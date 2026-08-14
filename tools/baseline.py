#!/usr/bin/env python3
"""Shoot a fixed set of cameras, every time the same way, so two runs can be compared.

    ~/imagegen/bin/python tools/baseline.py --url http://127.0.0.1:8080 \
        --views views.json --out shots/base

    views.json = [
      {"name": "spine-noon",  "eval": "game.goto('the_spine'); game.setHour(12)"},
      {"name": "spine-dusk",  "eval": "game.goto('the_spine'); game.setHour(19.5)"},
      {"name": "docks-noon",  "eval": "game.goto('docks');     game.setHour(12)"}
    ]

One file per view, named after it, nothing else in the directory. That is the whole point: a
directory of shots taken the same way is a thing you can diff against a later directory, and a
screenshot taken from wherever the camera happened to be is not.

Two uses:

  * **Before a performance pass.** Shoot the set, optimise, shoot it again, `imagediff.py` them.
    Anything that moved is either a bug you just wrote or a trade you are making deliberately.
  * **Every session.** The same set, re-shot, is how you see drift that no single change is
    responsible for — the slow slide nobody notices until the world looks worse than it did a
    week ago and nobody can say when.

Writes `manifest.json` alongside the images: the views, the renderer string, the viewport, and the
counters the page reported. A comparison between two sets taken on different renderers is not a
comparison, and this is how you find that out before drawing a conclusion from it.
"""
import argparse, json, pathlib, sys

GPU_ARGS = ["--enable-unsafe-webgpu", "--use-angle=metal", "--enable-features=Vulkan,WebGPU",
            "--ignore-gpu-blocklist"]

CAPS_JS = """() => {
  const gl = document.createElement('canvas').getContext('webgl2');
  const d = gl && gl.getExtension('WEBGL_debug_renderer_info');
  return { renderer: d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : (gl ? gl.getParameter(gl.RENDERER) : null),
           webgpu: !!navigator.gpu };
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--views", required=True, help="JSON file: [{name, eval, wait}]")
    ap.add_argument("--out", required=True, help="directory to write the shot set into")
    ap.add_argument("--report", help="JS evaluated after each view; stored in the manifest")
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=800)
    ap.add_argument("--wait", type=int, default=2000)
    a = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright is not importable by this interpreter. Try: ~/imagegen/bin/python " + " ".join(sys.argv))

    views = json.loads(pathlib.Path(a.views).read_text())
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.png"):
        old.unlink()

    errors, per_view = [], {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=GPU_ARGS)
        page = browser.new_page(viewport={"width": a.w, "height": a.h})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(a.url, wait_until="load", timeout=60000)
        page.wait_for_timeout(a.wait)
        caps = page.evaluate(CAPS_JS)

        for v in views:
            name = v.get("name") or f"view{len(per_view)}"
            if v.get("eval"):
                try:
                    page.evaluate(v["eval"])
                except Exception as e:
                    errors.append(f"{name}: {e}")
            page.wait_for_timeout(v.get("wait", a.wait))
            page.screenshot(path=str(out / f"{name}.png"))
            if a.report:
                try:
                    per_view[name] = page.evaluate(a.report)
                except Exception as e:
                    errors.append(f"{name} report: {e}")
            print(f"  {name}")
        browser.close()

    (out / "manifest.json").write_text(json.dumps({
        "url": a.url, "viewport": [a.w, a.h], "views": views,
        "renderer": caps.get("renderer"), "webgpu": caps.get("webgpu"),
        "report": per_view, "errors": errors,
    }, indent=2))
    print(f"wrote {len(views)} shots to {out}")
    print(f"renderer: {caps.get('renderer')}")
    if errors:
        print(f"-- {len(errors)} error(s) --")
        for e in errors[:10]:
            print("  " + e)


if __name__ == "__main__":
    main()
