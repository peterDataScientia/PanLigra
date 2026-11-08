"""3D interaction segments grounded in PLIP detection objects.

Never infer endpoints from a 2D figure or average residue positions. A segment is
exported only when PLIP exposes two real 3D endpoints and it matches a displayed
interaction by type, residue, and reported distance.
"""
from __future__ import annotations

import math


def _xyz(value):
    if value is None:
        return None
    try:
        p = [float(x) for x in value]
    except (TypeError, ValueError):
        return None
    return p if len(p) == 3 and all(math.isfinite(x) for x in p) else None


def _atom(obj):
    return _xyz(getattr(obj, "coords", None))


def _residue(item):
    try:
        return f"{str(item.restype).upper()}{int(item.resnr)}_{str(item.reschain).strip()}"
    except (ValueError, TypeError, AttributeError):
        return ""


def _records(plip):
    groups = [
        ("HB", list(getattr(plip, "hbonds_pdon", [])) + list(getattr(plip, "hbonds_ldon", []))),
        ("HPI", list(getattr(plip, "hydrophobic_contacts", []))),
        ("PS", list(getattr(plip, "pistacking", []))),
        ("PC", list(getattr(plip, "pication_laro", [])) + list(getattr(plip, "pication_paro", []))),
        ("SB", list(getattr(plip, "saltbridge_lneg", [])) + list(getattr(plip, "saltbridge_pneg", []))),
        ("WB", list(getattr(plip, "water_bridges", []))),
        ("XB", list(getattr(plip, "halogen_bonds", []))),
        ("MC", list(getattr(plip, "metal_complexes", []))),
    ]
    for kind, items in groups:
        for item in items:
            a = b = None
            distance = None
            try:
                if kind == "HB":
                    # Donor -> acceptor, both heavy atoms
                    a, b = _atom(item.d), _atom(item.a)
                    distance = item.distance_ad
                elif kind == "HPI":
                    a, b = _atom(item.bsatom), _atom(item.ligatom)
                    distance = item.distance
                elif kind == "PS":
                    a = _xyz(item.proteinring.center)
                    b = _xyz(item.ligandring.center)
                    distance = item.distance
                elif kind == "PC":
                    a, b = _xyz(item.ring.center), _xyz(item.charge.center)
                    distance = item.distance
                elif kind == "SB":
                    a, b = _xyz(item.positive.center), _xyz(item.negative.center)
                    distance = item.distance
                elif kind == "WB":
                    # Water bridges are two separate atom-water distances; do
                    # not misrepresent either one as a direct protein-ligand line.
                    continue
                elif kind == "XB":
                    a, b = _atom(item.acc.o), _atom(item.don.x)
                    distance = item.distance
                elif kind == "MC":
                    # Metal records require identifying the target location; do
                    # not draw a generic metal-ligand line from an ambiguous field.
                    continue
            except (AttributeError, TypeError, ValueError):
                continue
            try:
                d = float(distance)
            except (ValueError, TypeError):
                continue
            if a is None or b is None or not math.isfinite(d):
                continue
            measured = math.dist(a, b)
            if abs(measured - d) > 0.15:
                continue
            yield {"type": kind, "residue": _residue(item),
                   "start": a, "end": b, "distance": d}


def build_3d_interaction_segments(plip, scene):
    """Align PLIP 3D interactions with existing displayed 2D IDs.

    Multiple same-type/same-residue records are matched by their independently
    reported distances; no candidate is used twice. Distances which disagree
    are not forced into a match.
    """
    candidates = list(_records(plip))
    seen = set()
    output = []
    for item in scene.get("interactions", []):
        target_dist = item.get("originalDistance")
        if target_dist is None:
            continue
        try:
            target_dist = float(target_dist)
        except (ValueError, TypeError):
            continue
        compatible = [
            (abs(rec["distance"]-target_dist), i, rec)
            for i, rec in enumerate(candidates)
            if i not in seen
            and rec["type"] == item.get("type")
            and rec["residue"] == item.get("sourceResidue")
            and abs(rec["distance"]-target_dist) < 0.10
        ]
        if not compatible:
            continue
        delta, idx, rec = min(compatible, key=lambda x: (x[0], x[1]))
        seen.add(idx)
        output.append({**rec, "id": item["id"]})
    return output
