"""RCSB PDB discovery and source-preserving coordinate import for PanLigra.

The importer is intentionally separate from PLIP and the publication renderer:
structures downloaded from the PDB archive enter the existing PLIP pipeline
unchanged when legacy PDB coordinates are available. mmCIF is only converted
when legacy PDB format is unavailable, with both original and conversion saved.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import re

import requests

SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
DATA_URL = "https://data.rcsb.org/rest/v1/core/entry/"
DOWNLOAD_URL = "https://files.rcsb.org/download/"
MAX_BYTES = 25 * 1024 * 1024
_ID = re.compile(r"(?:[0-9][A-Z0-9]{3}|PDB_[A-Z0-9]{8})", re.ASCII)


class PDBDatabaseError(ValueError):
    """Safe user-facing errors when the structure cannot be imported."""


def normalize_id(value: str) -> str:
    identifier = (value or "").strip().upper()
    if not _ID.fullmatch(identifier):
        raise PDBDatabaseError("Enter a valid PDB ID such as 1LF2 or pdb_00001lf2.")
    return identifier


def _json(url: str, *, params: dict | None = None) -> dict:
    try:
        resp = requests.get(url, params=params, timeout=(5, 18))
        if resp.status_code == 204:
            return {}
        if resp.status_code == 404:
            raise PDBDatabaseError("The PDB entry could not be found.")
        if resp.status_code == 400:
            raise PDBDatabaseError("RCSB rejected the search; simplify the filters.")
        resp.raise_for_status()
        result = resp.json()
        if not isinstance(result, dict):
            raise PDBDatabaseError("RCSB returned an unexpected metadata format.")
        return result
    except (requests.RequestException, json.JSONDecodeError) as exc:
        raise PDBDatabaseError(
            "Could not reach the RCSB PDB database. Retry or upload a local PDB."
        ) from exc


def _term(attribute: str, operator: str, value):
    return {"type": "terminal", "service": "text",
            "parameters": {"attribute": attribute, "operator": operator, "value": value}}


def search(
    query: str,
    mode: str = "Keywords",
    *,
    organism: str = "",
    ligand_only: bool = True,
    start: int = 0,
    rows: int = 10,
) -> dict:
    """Search experimental entries; no full structures are downloaded here."""
    term = (query or "").strip()
    if not term:
        raise PDBDatabaseError("Enter a keyword, protein name, ligand ID or PDB ID.")
    if mode == "PDB ID":
        value = normalize_id(term)
        return {"ids": [value], "total": 1, "query": {"pdb_id": value}}
    if mode == "Keywords":
        node = {"type": "terminal", "service": "full_text",
                "parameters": {"value": term}}
    elif mode == "Protein name":
        node = _term("rcsb_polymer_entity.pdbx_description", "contains_phrase", term)
    elif mode == "Ligand name / ID":
        if re.fullmatch(r"[A-Za-z0-9]{3}", term):
            node = _term("rcsb_nonpolymer_entity_container_identifiers.nonpolymer_comp_id",
                         "exact_match", term.upper())
        else:
            node = _term("rcsb_nonpolymer_entity.pdbx_description", "contains_phrase", term)
    else:
        raise PDBDatabaseError("Invalid search mode.")

    nodes = [node]
    if organism.strip():
        nodes.append(_term("rcsb_entity_source_organism.ncbi_scientific_name",
                           "contains_phrase", organism.strip()))
    if ligand_only:
        nodes.append(_term("rcsb_entry_info.nonpolymer_entity_count", "greater", 0))
    payload = {
        "query": {"type": "group", "logical_operator": "and", "nodes": nodes},
        "return_type": "entry",
        "request_options": {
            "paginate": {"start": max(0, int(start)), "rows": max(1, min(25, int(rows)))},
            "results_content_type": ["experimental"],
        },
    }
    result = _json(SEARCH_URL, params={"json": json.dumps(payload)})
    return {
        "ids": [record["identifier"] for record in result.get("result_set", [])
                if record.get("identifier")],
        "total": int(result.get("total_count", 0)),
        "query": payload,
    }


def summary(pdb_id: str) -> dict:
    pdb_id = normalize_id(pdb_id)
    record = _json(DATA_URL + pdb_id)
    info = record.get("rcsb_entry_info") or {}
    structure = record.get("struct") or {}
    return {
        "PDB ID": pdb_id,
        "Title": structure.get("title") or "Not available",
        "Method": ", ".join(x.get("method", "") for x in record.get("exptl", [])
                            if x.get("method")) or "Not available",
        "Resolution (Å)": ", ".join(str(x) for x in
                                    (info.get("resolution_combined") or [])) or "Not available",
        "Nonpolymer types": info.get("nonpolymer_entity_count", 0),
    }


def summaries(ids: list[str]) -> list[dict]:
    """Metadata lookups may fail for individual structures without losing a search."""
    def safe_summary(pdb_id):
        try:
            return summary(pdb_id)
        except PDBDatabaseError:
            return {"PDB ID": pdb_id, "Title": "Metadata unavailable",
                    "Method": "Not available", "Resolution (Å)": "Not available",
                    "Nonpolymer types": "—"}
    with ThreadPoolExecutor(max_workers=5) as pool:
        return list(pool.map(safe_summary, ids))


def _fetch_bytes(pdb_id: str, extension: str) -> tuple[bytes, str]:
    url = f"{DOWNLOAD_URL}{pdb_id}.{extension}"
    try:
        with requests.get(url, timeout=(5, 30), stream=True) as response:
            if response.status_code in (404, 410):
                raise FileNotFoundError(url)
            response.raise_for_status()
            chunks, total = [], 0
            for chunk in response.iter_content(chunk_size=65536):
                total += len(chunk)
                if total > MAX_BYTES:
                    raise PDBDatabaseError(
                        "The archived structure exceeds PanLigra's 25 MB import limit."
                    )
                chunks.append(chunk)
        return b"".join(chunks), url
    except requests.RequestException as exc:
        raise PDBDatabaseError(
            "RCSB coordinate download failed. Retry or upload your structure."
        ) from exc


def _convert_cif_to_pdb(cif_bytes: bytes) -> bytes:
    """PLIP currently consumes legacy PDB; refuse conversions losing chain IDs."""
    try:
        import gemmi
        text = cif_bytes.decode("utf-8")
        if not text.lstrip().startswith("data_"):
            raise PDBDatabaseError("RCSB returned invalid mmCIF content.")
        structure = gemmi.make_structure_from_block(
            gemmi.cif.read_string(text).sole_block()
        )
        if not len(structure):
            raise PDBDatabaseError("The mmCIF entry contains no coordinate models.")
        if any(len(chain.name) != 1 for model in structure for chain in model):
            raise PDBDatabaseError(
                "This mmCIF entry has multi-character chain IDs that the legacy "
                "PDB/PLIP input cannot preserve reliably; import a compatible "
                "curated PDB complex instead."
            )
        converted = structure.make_pdb_string().encode("utf-8")
        if b"ATOM  " not in converted:
            raise PDBDatabaseError("The mmCIF entry does not contain protein atoms.")
        return converted
    except PDBDatabaseError:
        raise
    except (ValueError, RuntimeError, UnicodeDecodeError) as exc:
        raise PDBDatabaseError(
            "RCSB mmCIF coordinates could not be converted to a PLIP-compatible PDB."
        ) from exc


def download(pdb_id: str) -> dict:
    """Get deposited structure and provenance; never assume a ligand is present."""
    pdb_id = normalize_id(pdb_id)
    legacy = len(pdb_id) == 4
    if legacy:
        try:
            pdb_bytes, url = _fetch_bytes(pdb_id, "pdb")
        except FileNotFoundError:
            pdb_bytes = b""
        else:
            if not any(line.startswith(b"ATOM  ") for line in pdb_bytes.splitlines()):
                raise PDBDatabaseError("The downloaded PDB has no protein coordinates.")
            return {
                "pdb_id": pdb_id, "pdb_bytes": pdb_bytes,
                "original_bytes": pdb_bytes, "source_filename": f"{pdb_id}.pdb",
                "pdb_filename": f"{pdb_id}.pdb", "source_format": "PDB",
                "converted": False, "source_url": url,
                "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            }
    try:
        cif_bytes, url = _fetch_bytes(pdb_id, "cif")
    except FileNotFoundError as exc:
        raise PDBDatabaseError("The selected PDB structure is unavailable.") from exc
    pdb_bytes = _convert_cif_to_pdb(cif_bytes)
    return {
        "pdb_id": pdb_id, "pdb_bytes": pdb_bytes,
        "original_bytes": cif_bytes, "source_filename": f"{pdb_id}.cif",
        "pdb_filename": f"{pdb_id}_converted.pdb", "source_format": "mmCIF",
        "converted": True, "source_url": url,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
    }
