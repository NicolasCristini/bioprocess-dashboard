"""Preview the built static site (dist/) on 127.0.0.1 — a plain static server, like any host.

No headers or logic are added: the security policy is inside the page (meta CSP), exactly as on a real host.

usage: python3 scripts/serve.py [port] [--base /repo-name/]
       (with --base the site is served under that sub-path, to rehearse GitHub Pages)
"""
import functools
import http.server
import sys
from pathlib import Path

DIST = Path(__file__).resolve().parent.parent / "dist"


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".wasm": "application/wasm", ".mjs": "text/javascript", ".whl": "application/zip"}
    base = "/"

    def translate_path(self, path):
        p = path.split("?", 1)[0].split("#", 1)[0]
        if not p.startswith(self.base):
            return str(DIST / "__outside_base__")
        return super().translate_path("/" + p[len(self.base):])

    def send_error(self, code, message=None, explain=None):
        # behave like GitHub Pages / Netlify: unknown paths get 404.html (the app shell)
        page = DIST / "404.html"
        if code == 404 and page.exists():
            body = page.read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    base = "/"
    if "--base" in args:
        i = args.index("--base")
        base = args[i + 1]
        del args[i:i + 2]
    port = int(args[0]) if args else 8765
    Handler.base = base
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(DIST)))
    print(f"serving {DIST} at http://localhost:{port}{base}")
    server.serve_forever()
