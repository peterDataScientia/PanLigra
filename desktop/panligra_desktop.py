"""Windows desktop entry point for the bundled PanLigra Streamlit application."""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

PORT = 18763


def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def open_when_ready(port: int) -> None:
    for _ in range(100):
        time.sleep(0.3)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                webbrowser.open(f"http://127.0.0.1:{port}")
                return
        except OSError:
            continue


def main() -> None:
    root = bundle_root()
    os.chdir(root)
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_SERVER_ADDRESS", "127.0.0.1")
    os.environ.setdefault("STREAMLIT_SERVER_PORT", str(PORT))

    from streamlit.web import bootstrap

    threading.Thread(target=open_when_ready, args=(PORT,), daemon=True).start()
    bootstrap.run(
        str(root / "app.py"),
        False,
        [],
        {
            "server.headless": True,
            "server.address": "127.0.0.1",
            "server.port": PORT,
            "browser.gatherUsageStats": False,
            "server.fileWatcherType": "none",
        },
    )


if __name__ == "__main__":
    main()
