#!/usr/bin/env python3
"""Your eyes. Load a page in a real GPU-backed browser, look at it, write a PNG.

    python3 tools/shot.py http://localhost:8080 -o shots/street.png
    python3 tools/shot.py <url> -o shots/dusk.png --eval "window.game.setHour(19.5)" --wait 3000
    python3 tools/shot.py --gpu-info

Nothing else in this harness looks at your work for you. Read the PNG it writes — images
render for you. Then read the console output it prints, because a page can look plausible
while throwing an error every frame.

WHY THE FLAGS MATTER, and this is not optional: a headless Chromium launched with defaults
renders through SwiftShader, which is a CPU rasterizer. On this machine that means no WebGPU
adapter at all, a 8192 texture limit instead of 16384, and frame times that measure nothing.
This script always launches with the Metal/WebGPU flags. If you write your own sensor, carry
them over, and check the renderer string rather than assuming.

Run it with the interpreter that has playwright:  ~/imagegen/bin/python tools/shot.py ...
"""
import argparse, json, sys, pathlib

GPU_ARGS = [
    "--enable-unsafe-webgpu",
    "--use-angle=metal",
    "--enable-features=Vulkan,WebGPU",
    "--ignore-gpu-blocklist",
]

CAPS_JS = """() => {
  const out = {};
  const gl = document.createElement('canvas').getContext('webgl2');
  out.webgl2 = !!gl;
  if (gl) {
    const d = gl.getExtension('WEBGL_debug_renderer_info');
    out.renderer = d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
    out.maxTextureSize = gl.getParameter(gl.MAX_TEXTURE_SIZE);
  }
  out.webgpu = !!navigator.gpu;
  return out;
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", help="page to load (http://… or file://…)")
    ap.add_argument("-o", "--out", default="shot.png")
    ap.add_argument("--eval", dest="js", help="JS to run in the page before capture")
    ap.add_argument("--wait", type=int, default=2000, help="ms to wait after load (and after --eval)")
    ap.add_argument("--w", type=int, default=1600)
    ap.add_argument("--h", type=int, default=900)
    ap.add_argument("--dpr", type=float, default=1.0, help="device pixel ratio")
    ap.add_argument("--full", action="store_true", help="full-page rather than viewport")
    ap.add_argument("--gpu-info", action="store_true", help="report what the browser is rendering with, then exit")
    a = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("playwright is not importable by this interpreter. Try: ~/imagegen/bin/python " + " ".join(sys.argv))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=GPU_ARGS)
        page = browser.new_page(viewport={"width": a.w, "height": a.h}, device_scale_factor=a.dpr)

        logs, errors, failed = [], [], []
        page.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("requestfailed", lambda r: failed.append(f"{r.url} — {r.failure}"))

        if a.gpu_info or not a.url:
            # NOT about:blank, and NOT a data: URL. WebGPU is a secure-context feature and
            # neither of those is one, so navigator.gpu is simply absent there and the check
            # reports "no WebGPU" on a machine that has it. file:// and http://127.0.0.1
            # are both secure contexts; a plain http:// host is not.
            import tempfile, os
            tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w")
            tmp.write("<html><body>caps</body></html>")
            tmp.close()
            page.goto("file://" + tmp.name)
            caps = page.evaluate(CAPS_JS)
            caps["secureContext"] = page.evaluate("() => window.isSecureContext")
            os.unlink(tmp.name)
            print(json.dumps(caps, indent=2))
            browser.close()
            return

        page.goto(a.url, wait_until="load", timeout=60000)
        page.wait_for_timeout(a.wait)

        caps = page.evaluate(CAPS_JS)

        if a.js:
            try:
                page.evaluate(a.js)
            except Exception as e:
                errors.append(f"--eval failed: {e}")
            page.wait_for_timeout(a.wait)

        out = pathlib.Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out), full_page=a.full)
        browser.close()

    print(f"wrote {out}  ({a.w}x{a.h} @{a.dpr}x)")
    print(f"renderer: {caps.get('renderer')}   webgpu: {caps.get('webgpu')}   maxTexture: {caps.get('maxTextureSize')}")
    if "SwiftShader" in str(caps.get("renderer")):
        print("!! rendering on the CPU — this frame is not what a player would see")
    if errors:
        print(f"\n-- page errors ({len(errors)}) --")
        for e in errors[:20]:
            print("  " + e)
    if failed:
        print(f"\n-- failed requests ({len(failed)}) --")
        for f in failed[:20]:
            print("  " + f)
    if logs:
        print(f"\n-- console ({len(logs)}) --")
        for l in logs[:60]:
            print("  " + l)


if __name__ == "__main__":
    main()
