"""Explicit electronic stopping tables; never substitute nuclear or total loss.

Tables must be supplied with provenance and match the projectile and target.
No built-in fabricated SRIM database or uncontrolled extrapolation is provided.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class ElectronicStoppingTable:
    projectile_z: int
    target_id: str
    energy_ev: tuple[float, ...]
    stopping_ev_per_a: tuple[float, ...]
    source: str

    def __post_init__(self):
        e=np.asarray(self.energy_ev)
        s=np.asarray(self.stopping_ev_per_a)
        if (e.ndim != 1 or len(e)<2 or s.shape != e.shape
            or not np.all(np.isfinite(e)) or not np.all(np.isfinite(s))
            or not np.all(e>0) or not np.all(np.diff(e)>0) or not np.all(s>0)):
            raise ValueError("Table needs increasing positive energies and positive electronic losses")
        if type(self.projectile_z) is not int or not 1 <= self.projectile_z <= 118:
            raise ValueError("Invalid projectile Z")
        if not self.target_id.strip() or not self.source.strip():
            raise ValueError("Target identity and source are mandatory")

    def evaluate(self, energy_ev):
        """Log-log interpolation. Out-of-domain energies are errors, not clipped."""
        query=np.asarray(energy_ev,dtype=float)
        if (not np.all(np.isfinite(query)) or np.any(query < self.energy_ev[0])
            or np.any(query > self.energy_ev[-1])):
            raise ValueError("Energy outside the stopping table; no extrapolation allowed")
        return np.exp(np.interp(np.log(query),np.log(self.energy_ev),
                                np.log(self.stopping_ev_per_a)))
