"""Element weights and common compound targets for the setup UI.

Densities and binding energies are literature-style engineering estimates for
research setup convenience. They are not a proprietary SRIM material database
and must be checked before publication-grade use.
"""
ELEMENTS = {
    "H": {"z": 1, "mass_u": 1.008}, "He": {"z": 2, "mass_u": 4.0026},
    "Li": {"z": 3, "mass_u": 6.941}, "Be": {"z": 4, "mass_u": 9.0122},
    "B": {"z": 5, "mass_u": 10.81}, "C": {"z": 6, "mass_u": 12.011},
    "N": {"z": 7, "mass_u": 14.007}, "O": {"z": 8, "mass_u": 15.999},
    "F": {"z": 9, "mass_u": 18.998}, "Ne": {"z": 10, "mass_u": 20.180},
    "Na": {"z": 11, "mass_u": 22.990}, "Mg": {"z": 12, "mass_u": 24.305},
    "Al": {"z": 13, "mass_u": 26.982}, "Si": {"z": 14, "mass_u": 28.085},
    "P": {"z": 15, "mass_u": 30.974}, "S": {"z": 16, "mass_u": 32.065},
    "Cl": {"z": 17, "mass_u": 35.453}, "Ar": {"z": 18, "mass_u": 39.948},
    "K": {"z": 19, "mass_u": 39.098}, "Ca": {"z": 20, "mass_u": 40.078},
    "Sc": {"z": 21, "mass_u": 44.956}, "Ti": {"z": 22, "mass_u": 47.867},
    "V": {"z": 23, "mass_u": 50.942}, "Cr": {"z": 24, "mass_u": 51.996},
    "Mn": {"z": 25, "mass_u": 54.938}, "Fe": {"z": 26, "mass_u": 55.845},
    "Co": {"z": 27, "mass_u": 58.933}, "Ni": {"z": 28, "mass_u": 58.693},
    "Cu": {"z": 29, "mass_u": 63.546}, "Zn": {"z": 30, "mass_u": 65.38},
    "Ga": {"z": 31, "mass_u": 69.723}, "Ge": {"z": 32, "mass_u": 72.64},
    "As": {"z": 33, "mass_u": 74.922}, "Se": {"z": 34, "mass_u": 78.96},
    "Br": {"z": 35, "mass_u": 79.904}, "Kr": {"z": 36, "mass_u": 83.798},
    "Rb": {"z": 37, "mass_u": 85.468}, "Sr": {"z": 38, "mass_u": 87.62},
    "Y": {"z": 39, "mass_u": 88.906}, "Zr": {"z": 40, "mass_u": 91.224},
    "Nb": {"z": 41, "mass_u": 92.906}, "Mo": {"z": 42, "mass_u": 95.96},
    "Tc": {"z": 43, "mass_u": 98.0}, "Ru": {"z": 44, "mass_u": 101.07},
    "Rh": {"z": 45, "mass_u": 102.906}, "Pd": {"z": 46, "mass_u": 106.42},
    "Ag": {"z": 47, "mass_u": 107.868}, "Cd": {"z": 48, "mass_u": 112.411},
    "In": {"z": 49, "mass_u": 114.818}, "Sn": {"z": 50, "mass_u": 118.71},
    "Sb": {"z": 51, "mass_u": 121.76}, "Te": {"z": 52, "mass_u": 127.60},
    "I": {"z": 53, "mass_u": 126.904}, "Xe": {"z": 54, "mass_u": 131.29},
    "Cs": {"z": 55, "mass_u": 132.905}, "Ba": {"z": 56, "mass_u": 137.327},
    "La": {"z": 57, "mass_u": 138.905}, "Ce": {"z": 58, "mass_u": 140.116},
    "Hf": {"z": 72, "mass_u": 178.49}, "Ta": {"z": 73, "mass_u": 180.948},
    "W": {"z": 74, "mass_u": 183.84}, "Re": {"z": 75, "mass_u": 186.207},
    "Os": {"z": 76, "mass_u": 190.23}, "Ir": {"z": 77, "mass_u": 192.217},
    "Pt": {"z": 78, "mass_u": 195.084}, "Au": {"z": 79, "mass_u": 196.967},
    "Hg": {"z": 80, "mass_u": 200.59}, "Pb": {"z": 82, "mass_u": 207.2},
    "Bi": {"z": 83, "mass_u": 208.980}, "U": {"z": 92, "mass_u": 238.029},
}

LAYER_KEYS = ("name", "thickness_a", "density_g_cm3", "species")
LAYER_SPECIES_KEYS = ("symbol", "z", "mass_u", "amount", "displacement_ev", "lattice_ev", "surface_ev")


def _sp(symbol, amount, disp, lat, surf):
    e = ELEMENTS[symbol]
    return {"symbol": symbol, "z": e["z"], "mass_u": e["mass_u"], "amount": float(amount),
            "displacement_ev": float(disp), "lattice_ev": float(lat), "surface_ev": float(surf)}


COMPOUNDS = {
    "Si": {"density_g_cm3": 2.329, "species": [_sp("Si", 1, 15, 2.5, 4.7)]},
    "Ge": {"density_g_cm3": 5.323, "species": [_sp("Ge", 1, 15, 2.5, 3.9)]},
    "SiO2": {"density_g_cm3": 2.20, "species": [_sp("Si", 1, 15, 2.5, 4.7), _sp("O", 2, 28, 2.0, 2.0)]},
    "Si3N4": {"density_g_cm3": 3.17, "species": [_sp("Si", 3, 15, 2.5, 4.7), _sp("N", 4, 28, 2.0, 2.0)]},
    "GaAs": {"density_g_cm3": 5.32, "species": [_sp("Ga", 1, 10, 2.5, 3.0), _sp("As", 1, 10, 2.5, 3.0)]},
    "GaN": {"density_g_cm3": 6.15, "species": [_sp("Ga", 1, 10, 2.5, 3.0), _sp("N", 1, 28, 2.0, 2.0)]},
    "Al2O3": {"density_g_cm3": 3.95, "species": [_sp("Al", 2, 27, 2.0, 2.0), _sp("O", 3, 28, 2.0, 2.0)]},
    "SiC": {"density_g_cm3": 3.21, "species": [_sp("Si", 1, 15, 2.5, 4.7), _sp("C", 1, 28, 2.0, 2.0)]},
    "W": {"density_g_cm3": 19.30, "species": [_sp("W", 1, 90, 3.0, 8.7)]},
    "Cu": {"density_g_cm3": 8.96, "species": [_sp("Cu", 1, 30, 3.0, 3.5)]},
    "Au": {"density_g_cm3": 19.32, "species": [_sp("Au", 1, 35, 3.0, 3.8)]},
    "Al": {"density_g_cm3": 2.70, "species": [_sp("Al", 1, 27, 2.0, 2.0)]},
    "Ti": {"density_g_cm3": 4.54, "species": [_sp("Ti", 1, 30, 3.0, 4.9)]},
    "Fe": {"density_g_cm3": 7.87, "species": [_sp("Fe", 1, 40, 3.0, 4.3)]},
    "Ni": {"density_g_cm3": 8.90, "species": [_sp("Ni", 1, 40, 3.0, 4.4)]},
    "CH": {"density_g_cm3": 1.20, "species": [_sp("C", 1, 28, 2.0, 2.0), _sp("H", 1, 10, 1.0, 1.0)]},
    "CH2": {"density_g_cm3": 0.94, "species": [_sp("C", 1, 28, 2.0, 2.0), _sp("H", 2, 10, 1.0, 1.0)]},
    "Kapton": {"density_g_cm3": 1.42, "species": [_sp("C", 5, 28, 2.0, 2.0), _sp("H", 2, 10, 1.0, 1.0),
                                                  _sp("N", 1, 28, 2.0, 2.0), _sp("O", 2, 28, 2.0, 2.0)]},
    "H2O": {"density_g_cm3": 1.00, "species": [_sp("H", 2, 10, 1.0, 1.0), _sp("O", 1, 28, 2.0, 2.0)]},
    "StainlessSteel": {"density_g_cm3": 8.00, "species": [
        _sp("Fe", 1, 40, 3.0, 4.3), _sp("Cr", 0.18, 40, 3.0, 4.1),
        _sp("Ni", 0.10, 40, 3.0, 4.4), _sp("Mn", 0.02, 40, 3.0, 2.9)]},
}

_ALIASES = {
    "water": "H2O", "h2o": "H2O",
    "kapton": "Kapton", "polyimide": "Kapton",
    "stainless steel": "StainlessSteel", "stainlesssteel": "StainlessSteel",
    "photoresist": "CH", "photoresist-ch": "CH", "pr": "CH",
    "polyethylene": "CH2", "pe": "CH2",
    "thermal oxide": "SiO2", "oxide": "SiO2",
    "silicon": "Si", "tungsten": "W", "gold": "Au", "copper": "Cu", "aluminum": "Al", "aluminium": "Al",
}


def list_elements():
    return sorted(ELEMENTS)


def list_compounds():
    return sorted(COMPOUNDS)


def get_element(symbol):
    if symbol not in ELEMENTS:
        raise KeyError(symbol)
    return dict(ELEMENTS[symbol])


def _resolve(name):
    if name in COMPOUNDS:
        return name
    key = name.strip().lower()
    if key in _ALIASES:
        return _ALIASES[key]
    for compound in COMPOUNDS:
        if compound.lower() == key:
            return compound
    raise KeyError(name)


def layer_from_compound(name, thickness_a=20000.0, density_override=None):
    resolved = _resolve(name)
    c = COMPOUNDS[resolved]
    density = float(density_override) if density_override is not None else float(c["density_g_cm3"])
    if not (thickness_a > 0) or density <= 0:
        raise ValueError("thickness and density must be positive")
    return {
        "name": resolved,
        "thickness_a": float(thickness_a),
        "density_g_cm3": density,
        "species": [dict(s) for s in c["species"]],
    }


def layer_from_elements(species_list, thickness_a, density_g_cm3, name="Custom"):
    if not species_list:
        raise ValueError("species_list must be nonempty")
    if not (thickness_a > 0) or not (density_g_cm3 > 0):
        raise ValueError("thickness and density must be positive")
    seen = set()
    species = []
    for item in species_list:
        sym = item["symbol"]
        if sym not in ELEMENTS:
            raise KeyError(sym)
        if sym in seen:
            raise ValueError("repeated species in one layer")
        seen.add(sym)
        entry = {
            "symbol": sym,
            "z": int(item.get("z", ELEMENTS[sym]["z"])),
            "mass_u": float(item.get("mass_u", ELEMENTS[sym]["mass_u"])),
            "amount": float(item["amount"]),
            "displacement_ev": float(item.get("displacement_ev", 25.0)),
            "lattice_ev": float(item.get("lattice_ev", 3.0)),
            "surface_ev": float(item.get("surface_ev", 2.0)),
        }
        if entry["amount"] <= 0:
            raise ValueError("amount must be positive")
        if entry["lattice_ev"] >= entry["displacement_ev"]:
            raise ValueError("lattice binding must be less than displacement threshold")
        species.append(entry)
    return {"name": name, "thickness_a": float(thickness_a),
            "density_g_cm3": float(density_g_cm3), "species": species}
