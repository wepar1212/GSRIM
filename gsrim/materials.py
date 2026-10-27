"""Validated immutable material definitions. Depths A, energies eV, density g/cm3."""
from dataclasses import dataclass
import math
from .element_defaults import ELEMENT_RECORDS


def positive(value, name, allow_zero=False):
    if not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"{name} must be finite and {'nonnegative' if allow_zero else 'positive'}")


@dataclass(frozen=True)
class Species:
    symbol: str
    z: int
    mass_u: float
    displacement_ev: float
    lattice_ev: float
    surface_ev: float

    def __post_init__(self):
        if not self.symbol or type(self.z) is not int or not 1 <= self.z <= 118:
            raise ValueError("Species requires a label and integer atomic number 1..118")
        record=ELEMENT_RECORDS.get(self.symbol)
        if record is None or record['z']!=self.z:
            raise ValueError('Element symbol and atomic number must match the supported H..U table')
        positive(self.mass_u, "mass")
        positive(self.displacement_ev, "displacement energy")
        positive(self.lattice_ev, "lattice energy", True)
        positive(self.surface_ev, "surface energy", True)


@dataclass(frozen=True)
class Layer:
    thickness_a: float
    density_g_cm3: float
    species: tuple[Species, ...]
    stoichiometry: tuple[float, ...]

    def __post_init__(self):
        positive(self.thickness_a,"thickness")
        positive(self.density_g_cm3,"density")
        if not self.species or len(self.species) != len(self.stoichiometry):
            raise ValueError("Species and stoichiometry lengths must match and be nonempty")
        if len(set(s.z for s in self.species)) != len(self.species):
            raise ValueError("Repeated atomic numbers are not supported within a layer")
        for amount in self.stoichiometry:
            positive(amount,"stoichiometric amount")
        positive(sum(self.stoichiometry),'total stoichiometry')
        positive(self.number_density_a3,'computed atomic density')

    @property
    def fractions(self):
        total=sum(self.stoichiometry)
        return tuple(v/total for v in self.stoichiometry)

    @property
    def number_density_a3(self):
        average_mass=sum(s.mass_u*f for s,f in zip(self.species,self.fractions))
        return self.density_g_cm3*6.02214076e23/average_mass/1e24


@dataclass(frozen=True)
class Target:
    layers: tuple[Layer, ...]

    def __post_init__(self):
        if not self.layers:
            raise ValueError("Target must have at least one layer")
        right=0.
        for layer in self.layers:
            next_right=right+layer.thickness_a
            if not math.isfinite(next_right) or next_right<=right:
                raise ValueError('Layer boundaries must be finite and distinct at floating-point precision')
            right=next_right

    @property
    def thickness_a(self):
        return sum(layer.thickness_a for layer in self.layers)

    def locate(self, depth_a):
        """Half-open layers [left,right); -1 front vacuum, len(layers) back vacuum."""
        if not math.isfinite(depth_a):
            raise ValueError("Nonfinite depth")
        if depth_a < 0:
            return -1
        right=0.
        for index,layer in enumerate(self.layers):
            right += layer.thickness_a
            if depth_a < right:
                return index
        return len(self.layers)
