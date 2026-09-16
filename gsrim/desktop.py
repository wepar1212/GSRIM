"""GSRIM desktop shell: local engine + native window (no external browser).

Requires: pywebview. On Windows uses Microsoft Edge WebView2 runtime.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _free_port(preferred: int = 8765) -> int:
    for port in (preferred, preferred + 1, preferred + 2, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port if port else 0))
                return s.getsockname()[1] if port == 0 else port
            except OSError:
                continue
    return 0


def _start_server(port: int):
    # Import after path setup
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    from gsrim.server import App, make_handler
    from http.server import ThreadingHTTPServer

    app = App()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, app


def main():
    # Prefer project venv python when frozen with PyInstaller --onedir
    port = _free_port(int(os.environ.get("GSRIM_PORT", "8765")))
    if port == 0:
        print("No free port", file=sys.stderr)
        return 1

    httpd, app = _start_server(port)
    url = f"http://127.0.0.1:{port}"
    # Wait until server answers
    import urllib.request

    for _ in range(50):
        try:
            urllib.request.urlopen(url + "/api/token", timeout=0.2)
            break
        except Exception:
            time.sleep(0.05)

    try:
        import webview
    except ImportError:
        print("pywebview not installed. Falling back to system browser.")
        import webbrowser

        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
        return 0

    window = webview.create_window(
        "GSRIM — GPU Ion Transport",
        url,
        width=1440,
        height=920,
        min_size=(1100, 700),
        background_color="#f7f7f5",
        text_select=True,
    )
    webview.start(debug=bool(os.environ.get("GSRIM_DEBUG")))
    # Cleanup
    try:
        if app.simulation:
            app.simulation.cancel()
            if app.simulation.thread:
                app.simulation.thread.join(5)
    except Exception:
        pass
    httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
