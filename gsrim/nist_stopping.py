"""Parse NIST PSTAR/ASTAR HTML text tables into Se(E) series."""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np

NIST_DIR = Path(__file__).resolve().parents[1] / "data" / "stopping" / "nist"

# Density used by NIST for linearization (g/cm3) — from STAR material defaults.
# We read STOP(e) in MeV cm^2/g and store mass stopping; linearize at runtime
# with the project's actual density.

_ROW = re.compile(
    r"([0-9.]+E[+-][0-9]+)\s+([0-9.]+E[+-][0-9]+)\s+([0-9.]+E[+-][0-9]+)\s+"
    r"([0-9.]+E[+-][0-9]+)\s+([0-9.]+E[+-][0-9]+)\s+([0-9.]+E[+-][0-9]+)"
)

# Map GSRIM compound/element names to NIST file tags
NAME_TO_TAG = {
    "H": "H", "He": "He", "Be": "Be", "C": "C", "N": "N", "O": "O",
    "Al": "Al", "Si": "Si", "Ar": "Ar", "Ti": "Ti", "Fe": "Fe", "Cu": "Cu",
    "Ge": "Ge", "W": "W", "Pt": "Pt", "Au": "Au", "Pb": "Pb",
    "Al2O3": "Al2O3", "Kapton": "Kapton", "Polyethylene": "Polyethylene",
    "Water": "Water", "SiO2": "SiO2", "Si oxide": "SiO2", "Quartz": "SiO2",
    "Air": "Air", "Nylon": "Nylon",
}


def _parse_file(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    # Unescape common entities if any
    rows = []
    for m in _ROW.finditer(text):
        t, se, sn, st, rc, rp = (float(x) for x in m.groups())
        if t > 0 and se > 0:
            rows.append((t * 1.0e6, se))  # eV , MeV cm2/g
    if len(rows) < 5:
        return None
    rows.sort()
    e = np.array([r[0] for r in rows], dtype=float)
    sm = np.array([r[1] for r in rows], dtype=float)
    # dedupe
    keep = np.ones(len(e), dtype=bool)
    for i in range(1, len(e)):
        if e[i] <= e[i - 1] * (1 + 1e-12):
            keep[i] = False
    return e[keep], sm[keep]


def load_nist_index() -> dict:
    """Return {(projectile, target_tag): (E_eV, S_mass_MeV_cm2_g)}"""
    index = {}
    if not NIST_DIR.is_dir():
        return index
    for path in NIST_DIR.glob("PSTAR_*.html"):
        parts = path.stem.split("_", 2)
        if len(parts) < 3:
            continue
        tag = parts[-1]
        parsed = _parse_file(path)
        if parsed:
            index[("H", tag)] = parsed
    for path in NIST_DIR.glob("ASTAR_*.html"):
        parts = path.stem.split("_", 2)
        if len(parts) < 3:
            continue
        tag = parts[-1]
        parsed = _parse_file(path)
        if parsed:
            index[("He", tag)] = parsed
    return index


def mass_stopping_to_linear(s_mass, density_g_cm3):
    """MeV cm2/g -> eV/angstrom."""
    return s_mass * density_g_cm3 * 0.01


def get_se_series(projectile: str, target_name: str, density_g_cm3: float, index=None):
    """Return (E_eV, Se_eV_A) or None."""
    if index is None:
        index = load_nist_index()
    tag = NAME_TO_TAG.get(target_name, target_name)
    key = (projectile, tag)
    if key not in index:
        # try alias
        return None
    e, sm = index[key]
    se = mass_stopping_to_linear(sm, density_g_cm3)
    return e, se
