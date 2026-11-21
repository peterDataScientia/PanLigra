# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

root = Path(SPECPATH).resolve().parent
datas = []
binaries = []
hiddenimports = []

for package in ("streamlit", "plip", "openbabel", "rdkit", "cairo", "gemmi"):
    pkg_datas, pkg_bins, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_bins
    hiddenimports += pkg_hidden

for path in root.glob("*.py"):
    datas.append((str(path), "."))
datas.extend([
    (str(root / "assets"), "assets"),
    (str(root / ".streamlit"), ".streamlit"),
    (str(root / "VERSION.txt"), "."),
])

a = Analysis(
    [str(root / "desktop" / "panligra_desktop.py")],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + collect_submodules("streamlit"),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="PanLigra",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PanLigra")
