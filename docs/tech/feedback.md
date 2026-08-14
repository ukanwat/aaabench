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
~/imagegen/bin/python tools/shot.py <url> -o shots/drive.png --frames 300
~/imagegen/bin/python tools/shot.py <url> -o shots/x.png --report "<js>"
~/imagegen/bin/python tools/shot.py --gpu-info
```

Then **`Read` the PNG** — images render for you. It also prints every console message, page
error and failed request from the load, and the renderer string.

Use `~/imagegen/bin/python`, which is the interpreter with playwright installed.

**`--eval` runs any JavaScript in the page before capture; `--report` runs any JavaScript after
it and prints what it returns, as JSON.** Between them they drive and interrogate whatever
interface your game exposes — set the hour, force weather, teleport, start a mission, read your
own counters:

```bash
shot.py <url> -o shots/dusk.png \
  --eval  "game.setHour(19.5); game.setWeather('rain')" \
  --report "({ hour: game.hour, draws: renderer.info.render.calls,
                tris: renderer.info.render.triangles,
                textures: renderer.info.memory.textures })"
```

The harness deliberately knows nothing about what that interface is called or what shape it has.
Naming it is your decision — but note that a world you cannot drive from outside is a world you
can only photograph from wherever it happens to be pointing, and every comparison across sessions
then depends on getting the camera back to the same place by hand.

**`--frames N` needs no cooperation at all.** It installs a recorder before your code runs and
reports the distribution of the last N frame deltas:

```
-- frame time over 300 frames (ms) --
  p50 8.3   p95 9.3   p99 9.3   worst 9.3
```

Read the distribution, never the mean: a p50 of 8 ms with a p99 of 40 ms is a stutter problem,
and an average hides it completely. Frames are capped to the display refresh, so a p50 at the cap
means "at least this fast", not "exactly this fast" — and the first frames are dropped from the
sample because they pay for shader compilation and texture upload, which is a real cost but a
different measurement. See `.claude/skills/browser-profiling` for what the numbers can and cannot
tell you.

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
