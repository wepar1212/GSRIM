"""Build per-species/layer Se(E) grids and path primitives for the GPU kernel.

Output arrays (float64):
  E_grid [n]          energy eV, geometric
  Se_grid [n]         eV/A at E_grid
  Tau_grid [n]        path optical depth ∫_{E0}^{E} dE'/Se(E')  in angstrom
                      (Tau[0]=0 at E_grid[0])
  Se_cutoff           Se at cutoff (host)
  Tau_cutoff          Tau at cutoff (host)

Sources priority: IAEA series > Biersack-Varelas analytic > LS.
"""
from __future__ import annotations

import math
import numpy as np

from .electronic_stopping import (
    lindhard_scharff_coefficient,
    biersack_varelas_stopping,
    effective_z,
    mean_excitation_energy,
)
from .iaea_stopping import load_index, build_series, bragg_compound, find_iaea_csv
from .nist_stopping import load_nist_index, get_se_series

_INDEX_CACHE = None
_NIST_CACHE = None


def nist_index(force_reload=False):
    global _NIST_CACHE
    if _NIST_CACHE is None or force_reload:
        try:
            _NIST_CACHE = load_nist_index()
        except Exception:
            _NIST_CACHE = {}
    return _NIST_CACHE


def iaea_index(force_reload=False):
    global _INDEX_CACHE
    if _INDEX_CACHE is None or force_reload:
        if find_iaea_csv() is None:
            _INDEX_CACHE = {}
        else:
            try:
                _INDEX_CACHE = load_index()
            except Exception:
                _INDEX_CACHE = {}
    return _INDEX_CACHE


def se_for_pair(
    projectile_symbol: str,
    projectile_z: int,
    projectile_mass_u: float,
    target_species: list[tuple[str, int, float, float]],
    # list of (symbol, z, mass_u, atomic_fraction) for one layer
    number_density_a3: float,
    layer_density_g_cm3: float,
    energy_grid: np.ndarray,
    model: str = "auto",
):
    """Return Se(eV/A) on energy_grid for projectile in this layer.

    model: auto | iaea | biersack-varelas | lindhard-scharff
    """
    e = np.asarray(energy_grid, dtype=float)
    index = iaea_index()
    se = None
    source = "lindhard-scharff"

    # 1) NIST PSTAR/ASTAR for H and He in single-species layers
    if model in ("auto", "iaea") and projectile_symbol in ("H", "He") and len(target_species) == 1:
        hit = get_se_series(projectile_symbol, target_species[0][0], layer_density_g_cm3, nist_index())
        if hit is not None:
            e_n, se_n = hit
            lo, hi = float(e_n[0]), float(e_n[-1])
            if float(e[-1]) >= lo * 0.5:
                se_tab = np.exp(np.interp(np.log(np.clip(e, lo, hi)), np.log(e_n), np.log(se_n)))
                se, source = ("hybrid", se_tab, lo, hi), f"NIST:{projectile_symbol}/{target_species[0][0]}"

    # 2) IAEA experimental DB
    if model in ("auto", "iaea") and index and se is None:
        if len(target_species) == 1:
            sym = target_species[0][0]
            ser = build_series(index, projectile_symbol, sym, density_g_cm3=layer_density_g_cm3)
            if ser is not None and float(e[-1]) >= float(ser.energy_ev[0]) * 0.5:
                lo, hi = float(ser.energy_ev[0]), float(ser.energy_ev[-1])
                se_tab = np.exp(np.interp(np.log(np.clip(e, lo, hi)), np.log(ser.energy_ev), np.log(ser.se_ev_a)))
                se, source = ("hybrid", se_tab, lo, hi), f"IAEA:{projectile_symbol}/{sym}"
        else:
            fracs = [(s[0], s[3]) for s in target_species]
            from .iaea_stopping import ELEMENT_DENSITY
            dens = [ELEMENT_DENSITY.get(s[0], 0.)
                    for s in target_species]
            ser = bragg_compound(index, projectile_symbol, fracs, dens, number_density_a3=number_density_a3)
            if ser is not None and float(e[-1]) >= float(ser.energy_ev[0]) * 0.5:
                lo, hi = float(ser.energy_ev[0]), float(ser.energy_ev[-1])
                se_tab = np.exp(np.interp(np.log(np.clip(e, lo, hi)), np.log(ser.energy_ev), np.log(ser.se_ev_a)))
                se, source = ("hybrid", se_tab, lo, hi), "IAEA-Bragg"

    # Analytic fallback / low-energy fill
    z_list = [s[1] for s in target_species]
    fr = [s[3] for s in target_species]
    try:
        z2 = effective_z(z_list, fr)
        i_mean = mean_excitation_energy(z_list, fr)
    except ValueError:
        z2 = float(sum(z_list) / max(len(z_list), 1))
        i_mean = 0.0

    k_ls = 0.0
    for sym, z, m, frac in target_species:
        if frac > 0:
            k_ls += lindhard_scharff_coefficient(
                projectile_z, int(z), projectile_mass_u, number_density_a3 * frac
            )

    if se is None or (isinstance(se, tuple) and se[0] == "hybrid"):
        if model == "lindhard-scharff":
            se_analytic = k_ls * np.sqrt(e)
            src_a = "LS"
        else:
            se_analytic = biersack_varelas_stopping(
                e, k_ls, projectile_z, projectile_mass_u, number_density_a3, z2, ck=1.0
            )
            src_a = "BV"
            e_sw = 25.0e3 * max(projectile_mass_u, 1.0)
            w = np.clip(e / e_sw, 0.0, 1.0) ** 2
            se_ls = k_ls * np.sqrt(e)
            se_analytic = w * se_analytic + (1.0 - w) * se_ls
        if isinstance(se, tuple) and se[0] == "hybrid":
            se_tab, e_lo, e_hi = se[1], se[2], se[3]
            se_analytic = np.maximum(se_analytic, 1e-8)
            in_table = (e >= e_lo) & (e <= e_hi)
            se = np.where(in_table, se_tab, se_analytic)
            source += f" [{e_lo:g},{e_hi:g}]eV; outside={src_a}; fallback_nodes={int((~in_table).sum())}/{e.size}"
        else:
            se = se_analytic
            source = src_a
    se = np.maximum(se, 1e-8)
    return se, source


def build_tau(energy_grid, se_grid):
    """Trapezoidal optical depth from E[0]."""
    e = np.asarray(energy_grid, dtype=float)
    se = np.asarray(se_grid, dtype=float)
    tau = np.zeros_like(e)
    inv = 1.0 / se
    for i in range(1, len(e)):
        tau[i] = tau[i - 1] + 0.5 * (inv[i] + inv[i - 1]) * (e[i] - e[i - 1])
    return tau


def default_energy_grid(e_min=1.0, e_max=50e6, n=256):
    return np.geomspace(e_min, e_max, n)


def build_layer_tables(project_ion, layers, model="auto"):
    """For each layer build (E, Se, Tau) for every species index used on device.

    Returns dict with lists aligned to device species order.
    """
    ion_sym = project_ion.get("symbol", "?")
    ion_z = int(project_ion["z"])
    ion_m = float(project_ion["mass_u"])
    e_grid = default_energy_grid(max(1.0, project_ion.get("cutoff_hint", 1.0)),
                                 max(1e6, project_ion["energy_kev"] * 1000 * 4), 320)
    out = []
    for layer in layers:
        # layer may be Layer object or dict
        if hasattr(layer, "species"):
            species = [(s.symbol, s.z, s.mass_u, f) for s, f in zip(layer.species, layer.fractions)]
            n_a3 = layer.number_density_a3
            rho = layer.density_g_cm3
        else:
            species = []
            total = sum(s["amount"] for s in layer["species"])
            for s in layer["species"]:
                species.append((s["symbol"], s["z"], s["mass_u"], s["amount"] / total))
            # approximate number density
            avg_m = sum(s[2] * s[3] for s in species)
            n_a3 = layer["density_g_cm3"] * 6.02214076e23 / avg_m / 1e24
            rho = layer["density_g_cm3"]
        se, src = se_for_pair(ion_sym, ion_z, ion_m, species, n_a3, rho, e_grid, model=model)
        tau = build_tau(e_grid, se)
        out.append({"energy_ev": e_grid, "se_ev_a": se, "tau_a": tau, "source": src,
                    "n_a3": n_a3, "rho": rho})
    return out
