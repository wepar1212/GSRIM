"""Energy-grid electronic stopping for multi-regime GPU transport.

Builds Se(E) tables per projectile species and layer from:
- Lindhard–Scharff (low energy, analytic)
- optional Bethe blend (high energy)
- optional user ElectronicStoppingTable (must carry provenance)

The transport kernel integrates dE/ds = -Se(E) using the tabulated
primitive path function, so Se need not remain ∝ sqrt(E).
"""
from __future__ import annotations
import math
import numpy as np
from .electronic_stopping import (
    lindhard_scharff_coefficient,
    bethe_stopping,
    mean_excitation_energy,
    effective_z,
    MEAN_EXCITATION_EV,
)


def ls_stopping(energy_ev, k_ls):
    return k_ls * np.sqrt(np.asarray(energy_ev, dtype=float))


def blend_stopping(energy_ev, k_ls, z1, mass_u, number_density_a3, z2_mean, i_mean_ev,
                   e_peak_kev_per_u=80.0, use_bethe=True):
    """Smooth LS→Bethe join in energy. e_peak is where LS should fade out."""
    e = np.asarray(energy_ev, dtype=float)
    se_ls = ls_stopping(e, k_ls)
    if not use_bethe or number_density_a3 <= 0 or i_mean_ev <= 0:
        return se_ls
    # Energy per nucleon in keV/u
    e_per_u = e / (mass_u * 1000.0)
    # Weight: 1 at low E, →0 well above e_peak
    w = 1.0 / (1.0 + (e_per_u / e_peak_kev_per_u) ** 1.5)
    se_b = bethe_stopping(z1, mass_u, e, number_density_a3, z2_mean, i_mean_ev)
    # Bethe is invalid below tens of keV; force LS weight high there
    w = np.maximum(w, 1.0 - np.clip(e_per_u / 50.0, 0.0, 1.0))
    return w * se_ls + (1.0 - w) * se_b


def build_stopping_grid(
    energy_ev,
    k_ls,
    z1,
    mass_u,
    number_density_a3,
    target_z_list,
    target_fractions,
    use_bethe=False,
    e_peak_kev_per_u=80.0,
):
    """Return (E grid, Se grid, path primitive) for one species in one layer.

    path(E) ≈ ∫_{E_cutoff}^{E} dE'/Se(E') is rebuilt in the kernel from Se
    samples; here we also store cumulative path from the LOWEST energy up.
    """
    e = np.asarray(energy_ev, dtype=float)
    if target_z_list:
        z2 = effective_z(target_z_list, target_fractions)
        try:
            i_mean = mean_excitation_energy(target_z_list, target_fractions)
        except ValueError:
            i_mean = 0.0
            use_bethe = False
    else:
        z2, i_mean, use_bethe = 1.0, 0.0, False
    se = blend_stopping(e, k_ls, z1, mass_u, number_density_a3, z2, i_mean,
                        e_peak_kev_per_u=e_peak_kev_per_u, use_bethe=use_bethe)
    se = np.maximum(se, 1e-12)
    return e, se


def path_integral_from_grid(energy_grid, se_grid, e_from, e_to):
    """∫_{e_from}^{e_to} dE/Se(E) via trapezoid on log-ish energy grid.

    e_from < e_to means positive path while slowing from e_to down to e_from
    is handled by the caller; this returns ∫_{e_from}^{e_to} dE/Se > 0 when
    e_to > e_from.
    """
    if e_to <= e_from:
        return 0.0
    mask = (energy_grid >= e_from) & (energy_grid <= e_to)
    if mask.sum() < 2:
        # fall back to local Se
        se = np.interp(0.5 * (e_from + e_to), energy_grid, se_grid)
        return (e_to - e_from) / max(se, 1e-12)
    e = energy_grid[mask]
    se = se_grid[mask]
    inv = 1.0 / se
    return float(np.trapezoid(inv, e))
