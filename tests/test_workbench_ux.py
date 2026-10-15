"""UI workbench contract: editing workflows remain discoverable without altering data."""
from pathlib import Path
import re

APP = Path("app.py").read_text(encoding="utf-8")
EDITOR = Path("editor.html").read_text(encoding="utf-8")


def test_structure_workflow_stays_in_sidebar():
    assert "with st.sidebar:" in APP
    sidebar = APP.split("with st.sidebar:", 1)[1].split("result_key_payload =", 1)[0]
    assert 'st.radio("Input mode"' in sidebar
    assert "Search RCSB PDB" in sidebar
    assert "Upload receptor PDB / PDBQT" in sidebar
    assert "Upload ligand or Vina PDBQT" in sidebar
    assert 'with st.expander("Advanced · figure dimensions", expanded=False)' in sidebar
    assert 'st.button("Open interaction editor"' in sidebar
    assert "st.table(" not in sidebar
    assert 'format_func=lambda x: f"{x} · ' in sidebar


def test_editor_primary_controls_have_one_dom_identity():
    identifiers = (
        "pv-move", "pv-select", "pv-undo", "pv-redo", "pv-reset",
        "pv-add-bond", "pv-add-interaction", "pv-add-distance",
        "pv-add-text", "pv-add-arrow", "pv-style-toggle",
        "pv-clear-selection", "pv-load-json", "pv-json",
        "pv-svg", "pv-png", "pv-pdf", "pv-png-scale",
        "pv-interaction-width", "pv-interaction-width-value",
    )
    for identifier in identifiers:
        assert len(re.findall(r'id="' + identifier + '"', EDITOR)) == 1, identifier


def test_menus_preserve_editor_actions_and_provenance():
    assert EDITOR.count('<details class="pv-tool-menu') == 3
    assert "＋ Insert" in EDITOR
    assert ">Layout</summary>" in EDITOR
    assert ">Export</summary>" in EDITOR
    assert ">Inspector</button>" in EDITOR
    assert "Original detections remain" not in EDITOR
    assert "Detected interactions and manually added annotations remain distinct." in EDITOR
    assert "state.scientificData?.interactions" in EDITOR
    assert "state.customInteractions" in EDITOR


def test_locked_molecular_workflow_not_modified():
    assert 'scientific_df,scientific_tables=build_scientific_records(analysis_obj["my_interactions"])' in APP
    assert "scene,scene_root=build_editor_scene(" in APP
    assert "Molecular structure" in EDITOR
    assert "LOCKED — ORIGINAL CHEMICAL STRUCTURE" in EDITOR
    assert "scrolling=False" in APP
