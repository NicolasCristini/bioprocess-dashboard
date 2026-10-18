"""Serve web/ on 127.0.0.1 with a Content-Security-Policy that only allows this origin.

The browser itself then refuses any request to another host, so inputs cannot leave the machine
even by accident (e.g. a library that tries to load a font or send telemetry).

usage: python3 scripts/serve.py [port]
"""
import functools
import http.server
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
# Python sources mounted into the in-browser app (read-only). Nothing else outside web/ is served.
MOUNTS = {"app": ROOT / "app", "src/bioprocess": ROOT / "src" / "bioprocess"}


def manifest() -> list[str]:
    files = []
    for prefix, base in MOUNTS.items():
        files += [f"{prefix}/{p.relative_to(base).as_posix()}" for p in sorted(base.rglob("*.py"))
                  if "__pycache__" not in p.parts]
    return files
CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval' blob: data:",  # stlite's worker is an inline data: script
    "worker-src 'self' blob: data:",
    "connect-src 'self' blob: data:",
    "img-src 'self' data: blob:",
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' data:",
    "frame-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'none'",
])


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".wasm": "application/wasm", ".mjs": "text/javascript", ".whl": "application/zip"}

    def translate_path(self, path):
        clean = path.split("?", 1)[0].split("#", 1)[0].lstrip("/")
        for prefix, base in MOUNTS.items():
            if clean.startswith(prefix + "/"):
                target = (base / clean[len(prefix) + 1:]).resolve()
                if target.is_relative_to(base.resolve()) and target.suffix == ".py":
                    return str(target)
                return str(WEB / "__forbidden__")
        return super().translate_path(path)

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/manifest.json":
            body = json.dumps(manifest()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        # app routes (/results, /phases, ...) are client-side pages: serve the shell
        clean = self.path.split("?", 1)[0].strip("/")
        if clean and "." not in clean.rsplit("/", 1)[-1] and not Path(self.translate_path(self.path)).exists():
            self.path = "/index.html"
        super().do_GET()

    def end_headers(self):
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(WEB)))
    print(f"serving {WEB} on http://localhost:{port} (CSP: this origin only)")
    server.serve_forever()
