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
    assert 'with st.expander("Figure size", expanded=False)' in sidebar
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
    assert "Detected interactions and manually added annotations remain distinct." not in EDITOR
    assert "pv-interaction-table-body" in EDITOR
    assert "pv-origin-detected" in EDITOR
    assert "pv-origin-manual" in EDITOR
    assert "state.scientificData?.interactions" in EDITOR
    assert "state.customInteractions" in EDITOR


def test_locked_molecular_workflow_not_modified():
    assert 'scientific_df,scientific_tables=build_scientific_records(analysis_obj["my_interactions"])' in APP
    assert "scene,scene_root=build_editor_scene(" in APP
    assert "Molecular structure" in EDITOR
    assert "LOCKED — ORIGINAL CHEMICAL STRUCTURE" in EDITOR
    assert "Professional object controls" not in EDITOR
    assert "Edits change presentation, not detected PLIP interactions." not in EDITOR
    assert "scrolling=True" in APP
    assert 'st.markdown("### Editor")' not in APP


def test_app_clears_manual_style_prompts():
    visible_copy = [
        "Import a complex, select a binding site, and open the editor.",
        "Find experimental structures in the RCSB Protein Data Bank",
        "Select a structure from the results below.",
        "Choose a result and click **Load selected PDB structure**.",
        "Generated results remain available until",
        "Scientific interactions preserved · Presentation editable",
        "Molecular structure and PLIP records remain immutable during figure edits.",
    ]
    for phrase in visible_copy:
        assert phrase not in APP


def test_editor_has_no_embedded_manual_sections():
    manual_phrases = [
        "Professional object controls",
        "The legend is independently editable.",
        "Multiple interactions between the same residue and ligand atom are automatically",
        "Edits change presentation, not detected PLIP interactions.",
    ]
    for phrase in manual_phrases:
        assert phrase not in EDITOR


def test_main_workspace_has_no_decorative_placeholder_or_spinner_manual_text():
    assert 'panviz-title' in APP
    assert 'No structure loaded' not in APP
    assert 'workspace_empty' not in APP
    assert 'pv-empty-workspace' not in APP
    assert '⬡' not in APP
    assert 'Analyzing interactions…' not in APP
    assert 'with st.spinner(" "):' in APP


def test_editor_iframe_and_interaction_table_are_accessible():
    assert 'initial_h = max(1200, min(2300, canvas_h + 660))' in APP
    assert 'components.html(html, height=initial_h, scrolling=True)' in APP
    assert '#pv-interaction-table{width:100%;min-width:680px;' in EDITOR
    assert 'overscroll-behavior:contain' in EDITOR
    assert 'if(isOpen)interactionTableWrap.scrollTop=0;' in EDITOR
    assert "document.body?.scrollHeight||0" not in EDITOR
    assert "document.documentElement?.scrollHeight||0" not in EDITOR
