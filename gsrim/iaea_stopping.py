"""IAEA electronic-stopping database loader and Se(E) table builder.

Data: IAEA NDS Stopping Power Database (Montanari et al. NIMB 2024),
bulk CSV from https://www-nds.iaea.org/stopping/download/tuples
(v2026-01). Converted to GSRIM units: energy eV, Se eV/angstrom.

IAEA CSV uses mass stopping power MeV/(mg/cm^2) and energy MeV/u.
Linear Se [eV/A] = S_m [MeV cm^2/mg] * rho [g/cm^3] * 10.
Energy [eV] = (MeV/u) * mass_u * 1e6.
"""
from __future__ import annotations

import csv
import math
import pickle
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CSV_CANDIDATES = [
    ROOT / "data" / "stopping" / "extracted" / "StoppingPower.csv",
    ROOT / "data" / "stopping" / "StoppingPower.csv",
]
CACHE_PATH = ROOT / "data" / "stopping" / "iaea_index.npz"

# Approximate atomic masses for energy conversion when isotope mass missing.
ATOMIC_MASS = {
    "H": 1.008, "He": 4.0026, "Li": 6.94, "Be": 9.0122, "B": 10.81, "C": 12.011,
    "N": 14.007, "O": 15.999, "F": 18.998, "Ne": 20.18, "Na": 22.99, "Mg": 24.305,
    "Al": 26.982, "Si": 28.085, "P": 30.974, "S": 32.06, "Cl": 35.45, "Ar": 39.948,
    "K": 39.098, "Ca": 40.078, "Ti": 47.867, "Cr": 51.996, "Mn": 54.938, "Fe": 55.845,
    "Ni": 58.693, "Cu": 63.546, "Zn": 65.38, "Ga": 69.723, "Ge": 72.63, "As": 74.922,
    "Zr": 91.224, "Nb": 92.906, "Mo": 95.95, "Ag": 107.87, "In": 114.82, "Sn": 118.71,
    "I": 126.9, "Xe": 131.29, "Ba": 137.33, "Hf": 178.49, "Ta": 180.95, "W": 183.84,
    "Pt": 195.08, "Au": 196.97, "Pb": 207.2, "U": 238.03,
}

# Default densities g/cm3 for elemental linearization when table is mass stopping.
ELEMENT_DENSITY = {
    "H": 0.0000899, "He": 0.0001785, "Li": 0.534, "B": 2.34, "C": 2.267, "N": 0.001251,
    "O": 0.001429, "F": 0.001696, "Ne": 0.0009, "Na": 0.971, "Mg": 1.738, "Al": 2.70,
    "Si": 2.329, "P": 1.82, "S": 2.067, "Cl": 0.003214, "Ar": 0.001784, "K": 0.862,
    "Ca": 1.54, "Ti": 4.54, "Cr": 7.19, "Mn": 7.43, "Fe": 7.874, "Ni": 8.908, "Cu": 8.96,
    "Zn": 7.14, "Ga": 5.91, "Ge": 5.323, "Zr": 6.506, "Nb": 8.57, "Mo": 10.28,
    "Ag": 10.49, "In": 7.31, "Sn": 7.287, "I": 4.93, "Xe": 0.005887, "Ba": 3.51,
    "Hf": 13.31, "Ta": 16.69, "W": 19.25, "Pt": 21.45, "Au": 19.32, "Pb": 11.34,
    "U": 19.1,
}

# Common compound densities for mass-stopping linearization.
COMPOUND_DENSITY = {
    "SiO2": 2.20, "Si3N4": 3.17, "SiC": 3.21, "GaAs": 5.32, "GaN": 6.15, "GaP": 4.13,
    "Al2O3": 3.95, "Kapton": 1.42, "Mylar": 1.38, "Polyethylene": 0.94,
    "Polypropylene": 0.90, "Polystyrene": 1.05, "PVC": 1.3, "Teflon": 2.2,
    "Polycarbonate": 1.2, "Water": 1.0, "Air": 0.001205,
}


def find_iaea_csv() -> Path | None:
    for p in CSV_CANDIDATES:
        if p.is_file():
            return p
    return None


def _mass_for(projectile: str, ion_isotope: str) -> float:
    try:
        m = float(ion_isotope)
        if m > 0:
            return m
    except ValueError:
        pass
    return ATOMIC_MASS.get(projectile, 1.0)


def _density_for_target(target: str, phase: str) -> float:
    key = target.strip()
    if key in COMPOUND_DENSITY:
        return COMPOUND_DENSITY[key]
    if key in ELEMENT_DENSITY:
        rho = ELEMENT_DENSITY[key]
        # Gas-phase elemental tables: still use standard density for linear Se.
        return rho
    return 0.0


@dataclass
class StoppingSeries:
    projectile: str
    target: str
    energy_ev: np.ndarray
    se_ev_a: np.ndarray
    n_points: int
    sources: tuple[str, ...]

    def evaluate(self, energy_ev: float) -> float:
        """Log-log interpolation; clip to table edges with warning semantics."""
        e = float(energy_ev)
        if e <= 0:
            return 0.0
        e = min(max(e, self.energy_ev[0]), self.energy_ev[-1])
        return float(np.exp(np.interp(np.log(e), np.log(self.energy_ev), np.log(self.se_ev_a))))


def load_index(csv_path: Path | None = None) -> dict:
    """Return { (ion, target): list of (E_eV, Se_eV_A, year, ref) } after unit conversion."""
    csv_path = csv_path or find_iaea_csv()
    if csv_path is None:
        raise FileNotFoundError("IAEA StoppingPower.csv not found under data/stopping/")
    raw: dict[tuple[str, str], list[tuple[float, float, str, str]]] = {}
    with csv_path.open(encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ion = (row.get("projectile_name") or "").strip()
            target = (row.get("target_name") or "").strip()
            if not ion or not target:
                continue
            try:
                e_mev_u = float(row["energy"])
                # Prefer IAEA's standardized mass stopping MeV/(mg/cm^2)
                s_raw = row.get("stopping_power_converted") or row.get("stopping_power")
                s_mev = float(s_raw)
            except (KeyError, ValueError, TypeError):
                continue
            unit = (row.get("stopping_unit_converted") or row.get("stopping_unit") or "").strip().lower()
            # If only original unit available and it is eV/A, use directly.
            se = None
            if unit.startswith("ev/") or unit.startswith("ev/å") or unit.startswith("ev/a"):
                se = s_mev
            if se is None:
                # Mass stopping MeV cm^2/mg * rho[g/cm3] * 10 = eV/A
                mass_u = _mass_for(ion, row.get("ion_isotope") or "")
                rho = _density_for_target(target, row.get("phase") or "")
                if rho <= 0:
                    continue
                e_ev = e_mev_u * mass_u * 1.0e6
                se = s_mev * rho * 10.0
            else:
                mass_u = _mass_for(ion, row.get("ion_isotope") or "")
                e_ev = e_mev_u * mass_u * 1.0e6
            if not (math.isfinite(e_ev) and math.isfinite(se) and e_ev > 0 and se > 0):
                continue
            raw.setdefault((ion, target), []).append(
                (e_ev, se, row.get("publication_year") or "", row.get("ref_id") or "")
            )
    index: dict[tuple[str, str], StoppingSeries] = {}
    for key, rows in raw.items():
        rows.sort(key=lambda t: t[0])
        e, s, years, refs = [], [], set(), set()
        prev_e = None
        for ev, se, y, r in rows:
            if prev_e is not None and ev <= prev_e * (1 + 1e-12):
                # keep higher stopping if duplicate energy (conservative max)
                if e and abs(np.log(ev / prev_e)) < 1e-9:
                    s[-1] = max(s[-1], se)
                    continue
            e.append(ev)
            s.append(se)
            prev_e = ev
            if y:
                years.add(y)
            if r:
                refs.add(r)
        e = np.asarray(e, dtype=float)
        s = np.asarray(s, dtype=float)
        # Drop nonpositive after conversion
        m = (e > 0) & (s > 0) & np.isfinite(e) & np.isfinite(s)
        e, s = e[m], s[m]
        if e.size < 4:
            continue
        index[key] = StoppingSeries(
            projectile=key[0], target=key[1], energy_ev=e, se_ev_a=s,
            n_points=int(e.size), sources=tuple(sorted(refs)[:8]) or ("IAEA",),
        )
    return index


def build_series(index: dict, projectile: str, target: str, density_g_cm3: float | None = None) -> StoppingSeries | None:
    """Fetch IAEA series; optionally rescale mass→linear if caller density differs."""
    series = index.get((projectile, target))
    if series is None:
        return None
    if density_g_cm3 is None:
        return series
    rho0 = _density_for_target(target, "")
    if rho0 <= 0 or abs(rho0 - density_g_cm3) < 1e-9:
        return series
    scale = density_g_cm3 / rho0
    return StoppingSeries(
        projectile=projectile, target=target,
        energy_ev=series.energy_ev.copy(),
        se_ev_a=series.se_ev_a * scale,
        n_points=series.n_points, sources=series.sources,
    )


def bragg_compound(index: dict, projectile: str, species_fractions: list[tuple[str, float]],
                   densities: list[float], *, number_density_a3: float) -> StoppingSeries | None:
    """Bragg rule: Se_compound = n_compound * sum f_i * (Se_pure_i / n_pure_i).

    species_fractions: list of (element_symbol, atomic_fraction)
    densities: pure-element g/cm3 used when the index was linearized.
    number_density_a3: actual compound atomic density, not mass density.
    """
    # Convert pure-element linear stopping to per-atom cross section first.
    if not math.isfinite(number_density_a3) or number_density_a3 <= 0:
        raise ValueError("Actual compound number density is required")
    if len(densities) != len(species_fractions):
        raise ValueError("Element density list must match composition")
    if not math.isclose(sum(f for _, f in species_fractions), 1., rel_tol=1e-8):
        raise ValueError("Bragg composition must use normalized atomic fractions")
    pieces = []
    for (sym, frac), _rho in zip(species_fractions, densities):
        if frac <= 0:
            continue
        ser = index.get((projectile, sym))
        if ser is None:
            return None
        mass = ATOMIC_MASS.get(sym)
        if mass is None or not math.isfinite(_rho) or _rho <= 0:
            return None  # no invented density/mass for a missing element
        pure_n = _rho * 6.02214076e23 / mass / 1e24
        pieces.append((frac * number_density_a3 / pure_n, ser))
    if not pieces:
        return None
    # Common grid: geometric union of energies within overlapping decade
    e_min = max(p.energy_ev[0] for _, p in pieces)
    e_max = min(p.energy_ev[-1] for _, p in pieces)
    if e_max <= e_min:
        return None
    e = np.geomspace(e_min, e_max, 96)
    se = np.zeros_like(e)
    for frac, p in pieces:
        se += frac * np.exp(np.interp(np.log(e), np.log(p.energy_ev), np.log(p.se_ev_a)))
    return StoppingSeries(
        projectile=projectile, target="+".join(s for s, f in species_fractions if f > 0),
        energy_ev=e, se_ev_a=se, n_points=int(e.size),
        sources=("IAEA-Bragg",),
    )
