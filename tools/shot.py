#!/usr/bin/env python3
"""Your eyes. Load a page in a real GPU-backed browser, look at it, write a PNG.

    python3 tools/shot.py http://localhost:8080 -o shots/street.png
    python3 tools/shot.py <url> -o shots/dusk.png --eval "window.game.setHour(19.5)" --wait 3000
    python3 tools/shot.py <url> -o shots/drive.png --frames 300
    python3 tools/shot.py <url> -o shots/x.png --report "renderer.info"
    python3 tools/shot.py --gpu-info

`--eval` runs any JavaScript in the page before capture, and `--report` runs any JavaScript
after it and prints what it returns. Between them they can drive and interrogate whatever
interface your game exposes — set the hour, force weather, teleport, start a mission, read
your own counters. The harness deliberately knows nothing about what that interface is
called or what shape it has; naming it is your decision, not this tool's.

`--frames N` needs no cooperation at all: it installs a frame recorder before your code runs
and reports the distribution of the last N frame deltas. Read the distribution, not the mean —
a p50 of 8 ms with a p99 of 40 ms is a stutter problem, and the average hides it completely.

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

# Installed before any page script runs, so it measures the page rather than cooperating
# with it. Nothing here assumes anything about how the page is built.
FRAME_RECORDER = """
(() => {
  const d = []; let last = performance.now();
  const tick = now => { d.push(now - last); last = now; requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
  window.__aaabench_frames = d;
})();
"""


def percentiles(ms):
    s = sorted(ms)
    at = lambda q: s[min(len(s) - 1, int(len(s) * q))]
    return {"n": len(s), "p50": at(0.50), "p95": at(0.95), "p99": at(0.99), "worst": s[-1]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", help="page to load (http://… or file://…)")
    ap.add_argument("-o", "--out", default="shot.png")
    ap.add_argument("--eval", dest="js", help="JS to run in the page before capture")
    ap.add_argument("--report", help="JS evaluated after the wait; its return value is printed as JSON")
    ap.add_argument("--frames", type=int, metavar="N",
                    help="sample the last N frame deltas and report the distribution")
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

        if a.frames:
            page.add_init_script(FRAME_RECORDER)

        page.goto(a.url, wait_until="load", timeout=60000)
        page.wait_for_timeout(a.wait)

        caps = page.evaluate(CAPS_JS)

        if a.js:
            try:
                page.evaluate(a.js)
            except Exception as e:
                errors.append(f"--eval failed: {e}")
            page.wait_for_timeout(a.wait)

        frames = None
        if a.frames:
            deltas = page.evaluate("() => window.__aaabench_frames || []")
            # Drop the first few: they pay for shader compilation and texture upload,
            # which is a real cost but a different measurement from steady state.
            deltas = [d for d in deltas[5:] if d > 0][-a.frames:]
            frames = percentiles(deltas) if deltas else None

        report = None
        if a.report:
            try:
                report = page.evaluate(a.report)
            except Exception as e:
                errors.append(f"--report failed: {e}")

        out = pathlib.Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(out), full_page=a.full)
        browser.close()

    print(f"wrote {out}  ({a.w}x{a.h} @{a.dpr}x)")
    print(f"renderer: {caps.get('renderer')}   webgpu: {caps.get('webgpu')}   maxTexture: {caps.get('maxTextureSize')}")
    if "SwiftShader" in str(caps.get("renderer")):
        print("!! rendering on the CPU — this frame is not what a player would see")

    if frames:
        print(f"\n-- frame time over {frames['n']} frames (ms) --")
        print(f"  p50 {frames['p50']:.1f}   p95 {frames['p95']:.1f}   p99 {frames['p99']:.1f}"
              f"   worst {frames['worst']:.1f}")
        print("  requestAnimationFrame is capped to the display refresh, so a p50 at the cap"
              " means 'at least this fast', not 'exactly this fast'.")
    elif a.frames:
        print("\n-- no frames recorded: the page never called requestAnimationFrame --")

    if report is not None:
        print("\n-- report --")
        print(json.dumps(report, indent=2, default=str))
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
