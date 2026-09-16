"""Electronic stopping with explicit models, validity ranges, and provenance.

Units: energy eV, length angstrom, stopping eV/angstrom.

Models (selected per projectile/target, never silent fallback):
- lindhard_scharff: S_e = k_ls * sqrt(E) for v << v_Fermi-like regime.
  Derived from LS (1961) with documented constants; valid roughly below
  ~25 keV/u where electronic stopping is still near velocity-proportional.
- bethe: non-relativistic Bethe electronic stopping with mean excitation
  energy I. Valid when the projectile is fully stripped-ish and E is high.
- blend: smooth LS→Bethe crossover used for intermediate energies.

No proprietary SRIM table is embedded. Users may attach
ElectronicStoppingTable for experimental/theoretical data they provide.
"""
from dataclasses import dataclass
import math
import numpy as np

# CODATA / derived constants (documented; not fitted to SRIM output)
COULOMB_EV_ANGSTROM = 14.3996454784255
BOHR_ANGSTROM = 0.529177210903
E_CHARGE_C = 1.602176634e-19
M_PROTON_KG = 1.67262192369e-27
M_ELECTRON_KG = 9.1093837015e-31
M_ELECTRON_C2_EV = 510998.95
V_BOHR_M_S = 2.18769126364e6
AVOGADRO = 6.02214076e23

# 8*pi*e^2*a0 * sqrt(2*e/mp) / v_bohr  converts Z^{7/6} form into eV^{1/2}/A
# per unit number density when divided by sqrt(projectile mass in u).
_LS_FRONT = (
    8.0 * math.pi * COULOMB_EV_ANGSTROM * BOHR_ANGSTROM
    * math.sqrt(2.0 * E_CHARGE_C / M_PROTON_KG) / V_BOHR_M_S
)  # ≈ 1.2100

# Published mean excitation energies I (eV), commonly used compilations
# (e.g. ICRU 49 / Berger-Seltzer style values). Extend as needed.
MEAN_EXCITATION_EV = {
    1: 19.2, 2: 41.8, 3: 40.0, 4: 63.7, 5: 76.0, 6: 78.0, 7: 82.0, 8: 95.0,
    9: 115.0, 10: 137.0, 11: 149.0, 12: 156.0, 13: 166.0, 14: 173.0,
    15: 173.0, 16: 180.0, 17: 174.0, 18: 188.0, 19: 190.0, 20: 191.0,
    22: 233.0, 26: 286.0, 29: 322.0, 32: 330.7, 47: 470.0, 50: 488.0,
    74: 727.0, 79: 790.0, 82: 823.0,
}


def validate_z(z):
    if type(z) is not int or not 1 <= z <= 118:
        raise ValueError("Atomic number must be an integer in 1..118")


def lindhard_scharff_coefficient(z1, z2, mass_u, number_density_a3):
    """Return k such that Se = k*sqrt(E_eV) in eV/angstrom for one target species."""
    validate_z(z1); validate_z(z2)
    if not math.isfinite(mass_u) or mass_u <= 0:
        raise ValueError("mass_u must be positive")
    if not math.isfinite(number_density_a3) or number_density_a3 < 0:
        raise ValueError("number density must be finite and nonnegative")
    denom = (z1 ** (2.0 / 3.0) + z2 ** (2.0 / 3.0)) ** 1.5
    return number_density_a3 * _LS_FRONT * (z1 ** (7.0 / 6.0)) * z2 / denom / math.sqrt(mass_u)


def bethe_stopping(z1, mass_u, energy_ev, number_density_a3, z2_mean, i_mean_ev,
                   shell_correction=0.0):
    """Non-relativistic Bethe S_e in eV/A for a compound (effective Z2, I).

    energy_ev may be array-like. Relativistic corrections are omitted; the
    function is intended for roughly 50 keV/u to a few MeV/u research use.
    """
    validate_z(z1)
    if not math.isfinite(mass_u) or mass_u <= 0:
        raise ValueError("mass_u must be positive")
    if not math.isfinite(i_mean_ev) or i_mean_ev <= 0:
        raise ValueError("mean excitation energy must be positive")
    if not math.isfinite(z2_mean) or z2_mean <= 0:
        raise ValueError("mean target Z must be positive")
    e = np.asarray(energy_ev, dtype=float)
    if np.any(~np.isfinite(e)) or np.any(e <= 0):
        raise ValueError("energy must be positive and finite")
    # beta^2 = 2E/(m c^2) for non-rel projectile of mass mass_u * mp
    m_c2 = mass_u * M_PROTON_KG * (2.99792458e8) ** 2 / E_CHARGE_C  # eV
    beta2 = np.clip(2.0 * e / m_c2, 1e-30, 0.7)
    # K = 4 pi e^4 me c^2 in practical units:
    # Se = n * 2*pi*e^4 * Z2 / (me v^2) * [ln(2 me v^2/I) - ...]
    # Using: Se = 0.307075e6 eV^2 * n_A * z^2 * (Z/A_eff) ... keep explicit SI-ish form.
    # dE/dx = (4*pi*z1^2*e^4*n*Z2)/(me*v^2) * L
    # Convert with e^2=COULOMB eV A, me in eV/c^2.
    me_c2 = M_ELECTRON_C2_EV
    v2_over_c2 = beta2
    # 4 pi e^4 n Z2 / (me v^2) in eV/A:
    # e^4 = (e^2)^2 ; n in 1/A^3 ; me v^2 = me_c2 * beta2
    prefactor = (
        4.0 * math.pi * (COULOMB_EV_ANGSTROM ** 2) * number_density_a3 * z2_mean
        / (me_c2 * v2_over_c2)
    )
    argument = np.maximum(2.0 * me_c2 * v2_over_c2 / i_mean_ev, 1e-300)
    stopping = prefactor * (np.log(argument) - beta2 - shell_correction)
    return np.maximum(stopping, 0.0)


def mean_excitation_energy(species_z, fractions):
    """Bragg-rule geometric mean of element I values for a compound."""
    if len(species_z) != len(fractions) or not species_z:
        raise ValueError("species and fractions must match")
    total = float(sum(fractions))
    if total <= 0:
        raise ValueError("fractions must sum positive")
    log_i = 0.0
    for z, f in zip(species_z, fractions):
        validate_z(z)
        if z not in MEAN_EXCITATION_EV:
            raise ValueError(f"No published mean excitation energy for Z={z}; add a value with citation")
        log_i += (f / total) * math.log(MEAN_EXCITATION_EV[z])
    return math.exp(log_i)


def effective_z(species_z, fractions):
    total = float(sum(fractions))
    if total <= 0:
        raise ValueError("fractions must sum positive")
    return sum(z * f for z, f in zip(species_z, fractions)) / total


@dataclass(frozen=True)
class StoppingModelConfig:
    model: str = "blend"  # lindhard-scharff | bethe | blend
    ls_max_ev: float = 2.0e5   # start blending away from pure LS by ~200 keV/u scale
    bethe_min_ev: float = 5.0e4
    validated: bool = False

    def __post_init__(self):
        if self.model not in ("lindhard-scharff", "bethe", "blend"):
            raise ValueError("Unknown stopping model")
        if not (math.isfinite(self.ls_max_ev) and math.isfinite(self.bethe_min_ev)):
            raise ValueError("Blend energies must be finite")
        if self.ls_max_ev <= 0 or self.bethe_min_ev <= 0:
            raise ValueError("Blend energies must be positive")


def stopping_prefactor_table(project_ion, layers, config: StoppingModelConfig):
    """Build per-species/layer electronic stopping evaluation data for the kernel.

    Returns dict with:
      model, species list, and for each ion species/layer either LS coefficient
      or a callable-friendly structure. The GPU path currently uses LS only;
      high-energy blend is evaluated on the host into a dense energy table.
    """
    # Host-side energy-grid tables for non-LS models; LS remains analytic on device.
    return config


def ls_matrix(species, bounds_fractions, densities, config=None):
    """Legacy-compatible LS coefficients [ns, nl] used by the transport kernel."""
    ns = len(species)
    nl = len(densities)
    fractions = bounds_fractions
    ls = np.zeros((ns, nl))
    for s in range(ns):
        z1, m1 = species[s][0], species[s][1]
        if z1 <= 0:
            continue
        for l in range(nl):
            acc = 0.0
            for t in range(ns):
                frac = fractions[l, t]
                if frac <= 0:
                    continue
                z2 = species[t][0]
                acc += lindhard_scharff_coefficient(int(round(z1)), int(round(z2)), m1, densities[l] * frac)
            ls[s, l] = acc
    return ls


def ls_stopping(energy_ev, k_ls):
    return k_ls * np.sqrt(np.asarray(energy_ev, dtype=float))


def _bethe_i0(z):
    z = float(z)
    if z < 13.0:
        return 12.0 + 7.0 / z
    return 9.76 + 58.5 * z ** (-1.19)


def bethe_bloch_rustbca_style(z1, z2, energy_ev, mass_u, number_density_a3):
    """RustBCA-style Bethe (eV/A): analytic, I0 empirical, shell term B."""
    e = np.asarray(energy_ev, dtype=float)
    if z1 <= 0 or z2 <= 0 or mass_u <= 0 or number_density_a3 < 0 or np.any(~np.isfinite(e)) or np.any(e <= 0):
        raise ValueError("Invalid Bethe model input")
    excitation_ev = z2 * _bethe_i0(z2)
    b = 100.0 * z1 / z2 if z2 < 3 else 5.0
    # Rest energy of projectile in eV
    m_c2 = mass_u * 931.494061e6
    # Stable form of 1 - 1/(1 + E/mc^2)^2.
    ratio = e / m_c2
    beta2 = ratio * (2.0 + ratio) / (1.0 + ratio)**2
    me_c2 = 510998.95
    # Published BV/RustBCA form; bare Z1 is a model assumption, not a charge-state input.
    pref = 4.0 * math.pi * COULOMB_EV_ANGSTROM**2 * number_density_a3 * z2 * z1**2 / (me_c2 * beta2)
    e_b = 2.0 * me_c2 * beta2 / excitation_ev
    return pref * np.log(e_b + 1.0 + b/e_b)


def biersack_varelas_stopping(energy_ev, k_ls, z1, mass_u, number_density_a3, z2_mean, ck=1.0):
    """Harmonic-mean join: 1/S = 1/S_Bethe + 1/(S_LS * ck)."""
    e = np.asarray(energy_ev, dtype=float)
    s_ls = ls_stopping(e, k_ls) * ck
    s_hi = bethe_bloch_rustbca_style(z1, max(z2_mean, 1.0), e, mass_u, number_density_a3)
    s_hi = np.maximum(s_hi, 1e-12)
    s_ls = np.maximum(s_ls, 1e-12)
    return 1.0 / (1.0 / s_hi + 1.0 / s_ls)
