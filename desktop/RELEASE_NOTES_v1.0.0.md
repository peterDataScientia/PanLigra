# PanLigra v1.0.0 — Windows Desktop

First official Windows desktop release of PanLigra.

## What is included
- Native Windows installer (`PanLigra-Setup.exe`).
- Standalone application with bundled Python runtime; end users do not need Python, Conda, or micromamba.
- PLIP protein–ligand interaction analysis with RDKit/Open Babel support.
- Interactive 2D interaction editor, scientific records, and figure/project exports.
- User-level installation with Start Menu and Desktop shortcuts.

## Validation
- Windows PyInstaller build passed.
- Frozen executable local-server startup smoke test passed.
- NSIS setup generation passed.
- Publication renderer and scientific regression tests passed.

The build has **not** yet been manually tested by installing the setup file on a separate Windows PC, and full PLIP analyses/exports in the installed distribution have not yet been end-to-end validated.

## Download and installation
Download `PanLigra-Setup.exe` below and run it on Windows. No Python installation is required. Windows may show an unsigned-publisher warning because the installer is not code signed.

## Integrity
A SHA-256 checksum is provided alongside the installer in `PanLigra-Setup.exe.sha256`.

Build provenance: successful GitHub Actions run #44950892536.
