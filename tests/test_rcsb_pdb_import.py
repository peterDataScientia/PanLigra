"""RCSB database import is independent of PanLigra's locked scientific renderer."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import rcsb_pdb


PDB = (
    b"ATOM      1  N   GLY A   1      11.111  12.222  13.333  1.00 20.00           N\n"
    b"ATOM      2  CA  GLY A   1      12.111  12.222  13.333  1.00 20.00           C\n"
    b"ATOM      3  C   GLY A   1      13.111  12.222  13.333  1.00 20.00           C\n"
    b"HETATM    4  C1  LIG A 101      14.111  12.222  13.333  1.00 20.00           C\nEND\n"
)


def test_strict_pdb_id_validation_blocks_external_url_injection():
    assert rcsb_pdb.normalize_id(" 1lf2 ") == "1LF2"
    assert rcsb_pdb.normalize_id("pdb_00001lf2") == "PDB_00001LF2"
    for bad in ["../../etc/passwd", "http://evil.test", "", "abcd;rm -rf", "LIG"]:
        with pytest.raises(rcsb_pdb.PDBDatabaseError):
            rcsb_pdb.normalize_id(bad)


def test_keywords_search_uses_rcsb_api_and_includes_nonpolymer_filter(monkeypatch):
    captured = {}
    def fake_json(url, *, params=None):
        captured["url"] = url
        captured["payload"] = json.loads(params["json"])
        return {"result_set": [{"identifier": "1LF2"}], "total_count": 1}
    monkeypatch.setattr(rcsb_pdb, "_json", fake_json)
    result = rcsb_pdb.search(
        "plasmepsin", organism="Plasmodium falciparum", start=10
    )
    assert result["ids"] == ["1LF2"]
    assert result["total"] == 1
    assert captured["url"] == rcsb_pdb.SEARCH_URL
    nodes = captured["payload"]["query"]["nodes"]
    assert nodes[0]["service"] == "full_text"
    assert {x.get("parameters", {}).get("attribute") for x in nodes} >= {
        "rcsb_entity_source_organism.ncbi_scientific_name",
        "rcsb_entry_info.nonpolymer_entity_count",
    }
    assert captured["payload"]["request_options"]["paginate"] == {
        "start": 10, "rows": 10
    }


def test_direct_id_avoids_search_api_and_checks_input():
    assert rcsb_pdb.search("1LF2", mode="PDB ID")["ids"] == ["1LF2"]
    with pytest.raises(rcsb_pdb.PDBDatabaseError):
        rcsb_pdb.search("invalid", mode="PDB ID")


def test_archived_legacy_pdb_is_imported_byte_for_byte(monkeypatch):
    observed = []
    def fake_fetch(pdb_id, ext):
        observed.append((pdb_id, ext))
        return PDB, "https://files.rcsb.org/download/1LF2.pdb"
    monkeypatch.setattr(rcsb_pdb, "_fetch_bytes", fake_fetch)
    data = rcsb_pdb.download("1lf2")
    assert observed == [("1LF2", "pdb")]
    assert data["pdb_bytes"] == data["original_bytes"] == PDB
    assert data["source_format"] == "PDB"
    assert data["source_filename"] == "1LF2.pdb"
    assert not data["converted"]
    assert data["pdb_id"] == "1LF2"


def test_extended_id_uses_mmcif_and_preserves_original(monkeypatch):
    import gemmi
    source = gemmi.read_pdb_string(PDB.decode())
    original_cif = source.make_mmcif_document().as_string().encode()

    def fake_fetch(pdb_id, ext):
        assert pdb_id == "PDB_00001LF2"
        assert ext == "cif"
        return original_cif, "https://files.rcsb.org/download/PDB_00001LF2.cif"
    monkeypatch.setattr(rcsb_pdb, "_fetch_bytes", fake_fetch)
    data = rcsb_pdb.download("pdb_00001lf2")
    assert data["original_bytes"] == original_cif
    assert b"ATOM  " in data["pdb_bytes"]
    assert b"HETATM" in data["pdb_bytes"]
    assert data["converted"]
    assert data["source_format"] == "mmCIF"
    assert data["source_filename"].endswith(".cif")
    assert data["pdb_filename"].endswith(".pdb")


def test_legacy_404_falls_back_to_mmcif(monkeypatch):
    def fetch(pdb_id, ext):
        if ext == "pdb":
            raise FileNotFoundError("No legacy PDB entry")
        return b"data_1LF2\n", "https://files.rcsb.org/download/1LF2.cif"
    monkeypatch.setattr(rcsb_pdb, "_fetch_bytes", fetch)
    monkeypatch.setattr(rcsb_pdb, "_convert_cif_to_pdb", lambda x: PDB)
    data = rcsb_pdb.download("1LF2")
    assert data["converted"]
    assert data["original_bytes"].startswith(b"data_")


def test_bad_archive_content_cannot_flow_to_plip(monkeypatch):
    monkeypatch.setattr(rcsb_pdb, "_fetch_bytes", lambda *_: (b"<html>error</html>", "test"))
    with pytest.raises(rcsb_pdb.PDBDatabaseError, match="protein coordinates"):
        rcsb_pdb.download("1LF2")


def test_new_pdb_data_source_reuses_original_analysis_and_export():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text()
    assert "Search RCSB PDB" in source
    assert 'loaded["original_bytes"]' in source
    assert 'loaded["pdb_bytes"]' in source
    assert '"source_provenance": source_provenance' in source
    assert "plip_2d_interactions(" in source
    assert "build_editor_scene(" in source
    # The original publication renderer is not edited by this feature.
    assert 'st.dataframe(' not in source
