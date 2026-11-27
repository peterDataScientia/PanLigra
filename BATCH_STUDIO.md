# Batch Studio (preview)

From the repository root after installing PanLigra requirements:

```bash
python batch_studio.py --input docking_complexes --output PanLigra_batch.html
```

For complexes with multiple ligands use a CSV manifest with columns `id,path,site`. Paths are relative to the manifest, and site is the exact PLIP binding-site identifier (e.g. LIG:A:101). The input must be a complete PDB complex.

```python
from batch_studio import batch
batch([{"id": "example", "path": "complex.pdb", "site": "LIG:A:101"}], "batch.html")
```

Open the generated HTML in a desktop browser. Previous/Next captures the current layout; Save & Next marks an entry reviewed. Save editable HTML downloads a portable copy. Export all SVGs produces a ZIP including layout JSON and a failure report. Global style applies defaults while retaining per-object overrides. Original scientific scenes are retained separately.

Default offline mode excludes external 3Dmol and PDF libraries; native 2D editing and SVG export are intended to work offline. Use --online for the existing editor's network-dependent features. Separate receptor/ligand inputs and batch PNG/PDF export are not implemented in this preview. Partial failures are reported in a sidecar JSON and yield a nonzero exit code. Browser and real-complex validation is required before release.
