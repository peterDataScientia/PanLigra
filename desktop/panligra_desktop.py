"""Windows desktop entry point for the bundled PanLigra Streamlit application."""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

PORT = 18763


def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def open_desktop_window(url: str) -> None:
    """Prefer an Edge app-mode window with no URL bar, using Windows' built-in browser."""
    if sys.platform == "win32":
        roots = (
            os.environ.get("PROGRAMFILES(X86)", ""),
            os.environ.get("PROGRAMFILES", ""),
            os.environ.get("LOCALAPPDATA", ""),
        )
        candidates = [
            Path(directory) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            for directory in roots if directory
        ]
        for executable in candidates:
            if executable.is_file():
                try:
                    subprocess.Popen(
                        [str(executable), f"--app={url}", "--no-first-run"],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return
                except OSError:
                    pass
    webbrowser.open(url)


def open_when_ready(port: int) -> None:
    for _ in range(150):
        time.sleep(0.3)
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                open_desktop_window(f"http://127.0.0.1:{port}")
                return
        except OSError:
            continue


def main() -> None:
    root = bundle_root()
    os.chdir(root)
    # PyInstaller windowed mode has no console handles; give third-party
    # libraries writable streams and keep diagnostics in the user's profile.
    if getattr(sys, "frozen", False) and (sys.stdout is None or sys.stderr is None):
        logdir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "PanLigra"
        logdir.mkdir(parents=True, exist_ok=True)
        logfile = open(logdir / "panligra-desktop.log", "a", encoding="utf-8", buffering=1)
        if sys.stdout is None:
            sys.stdout = logfile
        if sys.stderr is None:
            sys.stderr = logfile
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_SERVER_ADDRESS"] = "127.0.0.1"
    os.environ["STREAMLIT_SERVER_PORT"] = str(PORT)

    from streamlit import config as st_config
    from streamlit.web import bootstrap

    st_config.set_option("server.port", PORT)
    st_config.set_option("server.address", "127.0.0.1")

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
