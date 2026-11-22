"""PanLigra Windows desktop: embedded WebView2 shell and private Streamlit worker.

The primary process is a genuine GUI (no command prompt or external browser).
A separate frozen subprocess runs the Streamlit server; this keeps the GUI loop
on the Windows main thread and makes shutdown predictable.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOST = "127.0.0.1"
PORT = 18763
SERVER_ARG = "--panligra-internal-server"
START_TIMEOUT_SECONDS = 60


def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def prepare_runtime(root: Path) -> None:
    os.chdir(root)
    os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"
    os.environ["STREAMLIT_SERVER_ADDRESS"] = HOST
    os.environ["STREAMLIT_SERVER_PORT"] = str(PORT)
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"


def log_path() -> Path:
    folder = Path(os.environ.get("LOCALAPPDATA") or str(Path.home())) / "PanLigra"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "panligra-desktop.log"


def run_server() -> None:
    root = bundle_root()
    prepare_runtime(root)
    # Windowed PyInstaller executables have no valid stdout/stderr handles.
    # Streamlit and native scientific packages need writable streams.
    with open(log_path(), "a", encoding="utf-8", buffering=1) as log:
        sys.stdout = log
        sys.stderr = log
        from streamlit import config as st_config
        from streamlit.web import bootstrap

        st_config.set_option("server.port", PORT)
        st_config.set_option("server.address", HOST)
        bootstrap.run(
            str(root / "app.py"),
            False,
            [],
            {
                "server.headless": True,
                "server.address": HOST,
                "server.port": PORT,
                "browser.gatherUsageStats": False,
                "server.fileWatcherType": "none",
            },
        )


def wait_until_ready(process: subprocess.Popen) -> bool:
    base = f"http://{HOST}:{PORT}"
    deadline = time.monotonic() + START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(base + "/_stcore/health", timeout=1) as response:
                if response.status != 200:
                    time.sleep(0.3)
                    continue
            with urllib.request.urlopen(base + "/", timeout=2) as response:
                page = response.read(300_000).decode("utf-8", errors="replace")
                if response.status == 200 and "streamlit" in page.lower():
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(0.4)
    return False


def main() -> None:
    root = bundle_root()
    prepare_runtime(root)
    if not (root / "app.py").is_file():
        raise RuntimeError(f"Bundled app.py missing at {root}")

    if getattr(sys, "frozen", False):
        command = [sys.executable, SERVER_ARG]
    else:
        command = [sys.executable, str(Path(__file__).resolve()), SERVER_ARG]

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    with open(log_path(), "a", encoding="utf-8", buffering=1) as log:
        worker = subprocess.Popen(
            command,
            cwd=str(root),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
    try:
        if not wait_until_ready(worker):
            raise RuntimeError(
                "PanLigra server did not provide its homepage. "
                f"See {log_path()} for startup diagnostics."
            )
        import webview

        webview.create_window(
            "PanLigra",
            f"http://{HOST}:{PORT}/",
            width=1280,
            height=820,
            min_size=(850, 600),
            background_color="#ffffff",
            text_select=True,
        )
        # Real embedded desktop window. Never launch Edge/Chrome externally.
        webview.start(gui="edgechromium", debug=False)
    finally:
        if worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=8)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)


if __name__ == "__main__":
    if SERVER_ARG in sys.argv[1:]:
        run_server()
    else:
        try:
            main()
        except Exception:
            import traceback
            with open(log_path(), "a", encoding="utf-8") as output:
                traceback.print_exc(file=output)
            raise
