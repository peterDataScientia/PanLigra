"""PanLigra public Python API and command-line launcher."""
import sys
from pathlib import Path

# Compatibility with legacy absolute imports in the source tree.
# Entry points load the package's original modules without changing the renderer.
def _legacy_path():
    root = str(Path(__file__).resolve().parent)
    if root not in sys.path:
        sys.path.insert(0, root)

_legacy_path()
from .panligra_version import PANLIGRA_VERSION as __version__

def batch(items, output, **kwargs):
    from .batch_studio import batch as run
    return run(items, output, **kwargs)

def main():
    import argparse
    import subprocess
    parser = argparse.ArgumentParser(prog="panligra")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("command", choices=["gui", "batch", "render"], nargs="?", default="gui")
    args, rest = parser.parse_known_args()
    root = Path(__file__).resolve().parent
    if args.command == "gui":
        return subprocess.call([sys.executable, "-m", "streamlit", "run", str(root / "app.py"), *rest])
    if args.command == "batch":
        from . import batch_studio
        sys.argv = ["panligra batch", *rest]
        return batch_studio.main()
    return subprocess.call([sys.executable, str(root / "PanLigra.py"), *rest])
