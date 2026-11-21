import sys

# RDKit must be loaded before PLIP/Open Babel on Linux to avoid native-library collisions.
from rdkit import Chem  # noqa: F401
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
