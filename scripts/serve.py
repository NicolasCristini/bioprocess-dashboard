"""Serve web/ on 127.0.0.1 with a Content-Security-Policy that only allows this origin.

The browser itself then refuses any request to another host, so inputs cannot leave the machine
even by accident (e.g. a library that tries to load a font or send telemetry).

usage: python3 scripts/serve.py [port]
"""
import functools
import http.server
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
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

    def end_headers(self):
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(WEB)))
    print(f"serving {WEB} on http://localhost:{port} (CSP: this origin only)")
    server.serve_forever()
