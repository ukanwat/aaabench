#!/usr/bin/env python3
"""Static file server for the workspace.

    python3 tools/serve.py                # serves ./workspace on :8080
    python3 tools/serve.py --dir . --port 8000

Three things it does that `python3 -m http.server` does not, each of which will cost you an
hour if it is missing:

  * MIME types for the formats a 3D page actually loads — .glb, .gltf, .ktx2, .basis, .hdr,
    .exr, .wasm, .ply, .splat. A .wasm served as text/plain fails to instantiate in a way
    that reads like a code bug.
  * COOP/COEP headers, which are what SharedArrayBuffer requires — threaded WASM physics
    will not start without them.
  * No-cache, so what you look at is what you just built rather than what you built an hour
    ago. Stale caching produces "my fix did nothing" bug hunts that have no bug in them.
"""
import argparse, functools, http.server, mimetypes, os, socketserver

TYPES = {
    ".glb": "model/gltf-binary",
    ".gltf": "model/gltf+json",
    ".ktx2": "image/ktx2",
    ".basis": "application/octet-stream",
    ".hdr": "image/vnd.radiance",
    ".exr": "image/x-exr",
    ".wasm": "application/wasm",
    ".ply": "application/octet-stream",
    ".splat": "application/octet-stream",
    ".js": "text/javascript",
    ".mjs": "text/javascript",
}
for ext, t in TYPES.items():
    mimetypes.add_type(t, ext)


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cross-Origin-Resource-Policy", "cross-origin")
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, format, *args):
        if not self.path.endswith((".png", ".jpg", ".ktx2")):
            super().log_message(format, *args)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="workspace")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()
    root = os.path.abspath(a.dir)
    os.makedirs(root, exist_ok=True)
    handler = functools.partial(Handler, directory=root)
    with Server(("127.0.0.1", a.port), handler) as httpd:
        print(f"serving {root} on http://127.0.0.1:{a.port}  (COOP/COEP on, no-store)")
        httpd.serve_forever()
