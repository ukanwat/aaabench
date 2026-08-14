# Seeing your own work

There is no editor and no viewport. Nothing looks at the frame unless you make it. These two
tools exist so that you can start; everything past them is yours to build.

## The server

```bash
python3 tools/serve.py                     # serves ./workspace on http://127.0.0.1:8080
python3 tools/serve.py --dir . --port 8000
```

It sets three things a plain static server does not, each of which costs an hour when missing:
MIME types for `.glb`, `.gltf`, `.ktx2`, `.wasm`, `.hdr`, `.exr`, `.ply`, `.splat`; COOP and COEP
headers, which is what `SharedArrayBuffer` requires and therefore what threaded WASM needs; and
`no-store`, so what you look at is what you last built.

## The eye

```bash
~/imagegen/bin/python tools/shot.py http://127.0.0.1:8080 -o shots/street.png
~/imagegen/bin/python tools/shot.py <url> -o shots/dusk.png --eval "<js>" --wait 3000
~/imagegen/bin/python tools/shot.py --gpu-info
```

Then **`Read` the PNG** — images render for you. It also prints every console message, page
error and failed request from the load, and the renderer string.

Use `~/imagegen/bin/python`, which is the interpreter with playwright installed.

`--eval` runs arbitrary JavaScript in the page before capture. That is how you point the camera,
set the hour, force weather, or step a system — through whatever interface you decide to expose.
The harness does not know or care what that interface is.

## The trap that would have poisoned every frame

**A headless Chromium launched with default flags renders through SwiftShader, a CPU
rasterizer.** Measured on this machine:

| Launch | Renderer | Max texture | WebGPU adapter |
|---|---|---|---|
| default | `ANGLE (Google, SwiftShader driver)` | 8192 | **null** |
| `--enable-unsafe-webgpu --use-angle=metal` | `ANGLE Metal Renderer: Apple M4 Max` | 16384 | present |

So with defaults there is no WebGPU at all, half the texture limit, and frame times that measure
a CPU. `tools/shot.py` always launches with the flags and prints the renderer string; it says so
loudly if it ends up on SwiftShader. **If you write your own sensor, carry the flags over and
check the string** rather than assuming — a screenshot from the software rasterizer looks like a
screenshot, and it is the single most expensive way to be wrong about your own work.

## Sensors worth having that do not exist yet

Not a specification — a note that these are cheap to write and nobody else will write them:
a contact sheet of every district from a fixed camera, a turntable, a before/after pair from the
same position, a frame-time trace across a drive, a memory-and-draw-call readout, a night/day
pair of the same street, a stills set you can put beside a photograph.
