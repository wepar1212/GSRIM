"""Independent validation targets and convergence helpers.

Reference values are literature/agency data, not SRIM output and not fitted
to GSRIM. NIST PSTAR/ASTAR projected-range style values follow ICRU 49
methods (https://physics.nist.gov/PhysRefData/Star/Text/).

Important: those tabulations are continuous-slowing-down / transport-theory
ranges. A binary-collision Monte Carlo at the same energy will differ because
of discrete nuclear collisions, straggling, and different electronic stopping.
Agreement within tens of percent at moderate energy is informative; exact
equality is neither expected nor desirable to force.
"""
from dataclasses import dataclass
import copy
import math
from .project import DEFAULT, validate
from .simulation import Simulation


@dataclass(frozen=True)
class RangeTarget:
    ion_symbol: str
    ion_z: int
    ion_mass_u: float
    target_symbol: str
    target_z: int
    target_mass_u: float
    target_density_g_cm3: float
    energy_kev: float
    projected_range_nm: float
    source: str
    quantity: str = "projected range (ICRU-49 / NIST PSTAR-ASTAR style)"

    def ratio(self, measured_nm):
        if measured_nm is None or not math.isfinite(measured_nm):
            return None
        return measured_nm / self.projected_range_nm


# Verified NIST ASTAR/PSTAR-style targets (He/H in Si), depths at 2.33 g/cm3.
VALIDATION_TARGETS = [
    RangeTarget("He", 2, 4.0026, "Si", 14, 28.085, 2.329, 10.0, 103.9,
                "NIST ASTAR / ICRU 49 methods"),
    RangeTarget("He", 2, 4.0026, "Si", 14, 28.085, 2.329, 50.0, 410.6,
                "NIST ASTAR / ICRU 49 methods"),
    RangeTarget("He", 2, 4.0026, "Si", 14, 28.085, 2.329, 100.0, 665.2,
                "NIST ASTAR / ICRU 49 methods"),
    RangeTarget("H", 1, 1.00794, "Si", 14, 28.085, 2.329, 10.0, 125.5,
                "NIST PSTAR / ICRU 49 methods"),
    RangeTarget("H", 1, 1.00794, "Si", 14, 28.085, 2.329, 50.0, 454.1,
                "NIST PSTAR / ICRU 49 methods"),
]


def project_for_target(target: RangeTarget, ions=8192, thickness_a=None, mode="ions"):
    """Build a GSRIM project thick enough for the reference range."""
    p = copy.deepcopy(DEFAULT)
    p["name"] = f"Validation {target.ion_symbol} in {target.target_symbol} @ {target.energy_kev:g} keV"
    p["ion"] = {
        "symbol": target.ion_symbol,
        "z": target.ion_z,
        "mass_u": target.ion_mass_u,
        "energy_kev": target.energy_kev,
        "angle_deg": 0.0,
    }
    # Amorphous elemental target; displacements unused in ions mode.
    p["layers"] = [{
        "name": target.target_symbol,
        "thickness_a": float(thickness_a if thickness_a is not None
                             else max(5000.0, 8.0 * target.projected_range_nm * 10.0)),
        "density_g_cm3": target.target_density_g_cm3,
        "species": [{
            "symbol": target.target_symbol,
            "z": target.target_z,
            "mass_u": target.target_mass_u,
            "amount": 1.0,
            "displacement_ev": 25.0 if target.target_z == 14 else 40.0,
            "lattice_ev": 3.0,
            "surface_ev": 4.7,
        }],
    }]
    p["run"] = {
        "ions": int(ions),
        "seed": 12345,
        "batch_size": min(16384, max(1024, int(ions))),
        "bins": 200,
        "cutoff_ev": 3.0,
        "max_events": 100000,
        "mode": mode,
        "impact_scale": 1.0,
    }
    p["physics"] = {"stopping": "lindhard-scharff", "scattering": "table", "validated": False}
    validate(p)
    return p


def run_range_comparison(target: RangeTarget, ions=8192, timeout_s=180.0, mode="ions"):
    """Run one validation case and return a structured comparison."""
    project = project_for_target(target, ions=ions, mode=mode)
    sim = Simulation(project)
    sim.start()
    sim.thread.join(timeout_s)
    if sim.thread.is_alive():
        sim.cancel()
        sim.thread.join(30)
        raise RuntimeError(f"Validation run timed out for {target}")
    if sim.status != "completed":
        raise RuntimeError(f"Validation run failed: {sim.status} {sim.error}")
    snap = sim.snapshot()
    stats = snap["stats"]
    measured = stats["mean_range_nm"]
    return {
        "ion": f"{target.ion_symbol} ({target.ion_z})",
        "target": f"{target.target_symbol}",
        "energy_kev": target.energy_kev,
        "ions": ions,
        "mode": mode,
        "reference_nm": target.projected_range_nm,
        "measured_mean_range_nm": measured,
        "measured_std_nm": stats["range_std_nm"],
        "measured_se_nm": stats["mean_range_se_nm"],
        "ratio_measured_over_reference": target.ratio(measured),
        "source": target.source,
        "quantity": target.quantity,
        "max_energy_error_ev": stats["max_energy_error_ev"],
        "implanted": stats["implanted"],
        "backscattered": stats["backscattered"],
        "notes": [
            "NIST/ICRU values are transport-theory projected ranges, not BCA Monte Carlo means.",
            "GSRIM uses ZBL nuclear + Lindhard-Scharff electronic stopping; model differences are expected.",
            "Do not rescale GSRIM to force agreement; report the ratio.",
        ],
    }


def convergence_impact_scale(project, scales=(0.8, 1.0, 1.25), ions=2048):
    """Check that global physics is stable when the geometric impact scale moves."""
    results = []
    for scale in scales:
        p = copy.deepcopy(project)
        p["run"]["ions"] = ions
        p["run"]["impact_scale"] = scale
        validate(p)
        sim = Simulation(p)
        sim.start(); sim.thread.join(180)
        if sim.status != "completed":
            raise RuntimeError(f"Convergence run failed at scale={scale}: {sim.error}")
        stats = sim.snapshot()["stats"]
        results.append({
            "impact_scale": scale,
            "mean_range_nm": stats["mean_range_nm"],
            "displacements_per_ion": stats["displacements_per_ion"],
            "max_energy_error_ev": stats["max_energy_error_ev"],
        })
    ranges = [r["mean_range_nm"] for r in results if r["mean_range_nm"] is not None]
    spread = (max(ranges) - min(ranges)) / (sum(ranges)/len(ranges)) if ranges else None
    return {"results": results, "relative_range_spread": spread}
