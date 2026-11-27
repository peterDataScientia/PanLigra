"""Compatibility shim for Open Babel distributions lacking InChIKey output."""
import re
import warnings

def ensure_inchikey_support():
    from rdkit import Chem
    from rdkit.Chem import inchi
    from openbabel import pybel
    original = pybel.Molecule.write
    if getattr(original, "_panligra_inchikey", False):
        return
    try:
        key = pybel.readstring("smi", "CCO").write("inchikey").strip()
        if re.fullmatch(r"[A-Z]{14}-[A-Z]{10}-[A-Z]", key):
            return
    except (ValueError, RuntimeError):
        pass
    def write(self, format="smi", filename=None, overwrite=False, opt=None):
        if str(format).lower() != "inchikey" or filename is not None:
            return original(self, format, filename, overwrite, opt or {})
        smiles = original(self, "can").strip().split()
        mol = Chem.MolFromSmiles(smiles[0]) if smiles else None
        if mol is None:
            raise ValueError("Cannot derive InChIKey from Open Babel canonical SMILES")
        key = inchi.MolToInchiKey(mol)
        if not re.fullmatch(r"[A-Z]{14}-[A-Z]{10}-[A-Z]", key or ""):
            raise ValueError("RDKit failed to derive a valid InChIKey")
        return key + "\n"
    write._panligra_inchikey = True
    pybel.Molecule.write = write
    warnings.warn("Open Babel InChIKey output unavailable; using RDKit on Open Babel canonical SMILES for ligand identity metadata.", RuntimeWarning)
