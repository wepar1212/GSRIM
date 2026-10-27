"""Element weights and common compound targets for the setup UI.

Individual elements use the audited, source-labelled suggestions in
 element_defaults.py. Compound-specific presets retain their explicit values;
these are setup assumptions and require material-specific verification.
"""
from .element_defaults import ELEMENT_RECORDS, binding_defaults

ELEMENTS = {symbol: {"z": record["z"], "mass_u": record["mass_u"]}
            for symbol, record in ELEMENT_RECORDS.items()}

LAYER_KEYS = ("name", "thickness_a", "density_g_cm3", "species")
LAYER_SPECIES_KEYS = ("symbol", "z", "mass_u", "amount", "displacement_ev", "lattice_ev", "surface_ev")


def species_from_element(symbol, amount=1.0):
    """Build an editable row; unknown energy suggestions remain None."""
    element = ELEMENTS[symbol]
    return {"symbol": symbol, **element, "amount": float(amount), **binding_defaults(symbol)}


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

# Single-element dictionary entries must agree with adding that element.
# Explicit compound presets are not replaced by pure-element suggestions.
for _name, _compound in COMPOUNDS.items():
    if _name in ELEMENTS and len(_compound["species"]) == 1:
        _compound["species"] = [species_from_element(_name)]


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
        defaults = binding_defaults(sym)
        entry = {
            "symbol": sym,
            "z": int(item.get("z", ELEMENTS[sym]["z"])),
            "mass_u": float(item.get("mass_u", ELEMENTS[sym]["mass_u"])),
            "amount": float(item["amount"]),
            "displacement_ev": item.get("displacement_ev", defaults["displacement_ev"]),
            "lattice_ev": item.get("lattice_ev", defaults["lattice_ev"]),
            "surface_ev": item.get("surface_ev", defaults["surface_ev"]),
        }
        for key in ("displacement_ev", "lattice_ev", "surface_ev"):
            if entry[key] is None:
                raise ValueError(f"{sym}: {key} is unavailable; supply a material-specific value")
            entry[key] = float(entry[key])
        if entry["amount"] <= 0:
            raise ValueError("amount must be positive")
        if entry["lattice_ev"] >= entry["displacement_ev"]:
            raise ValueError("lattice binding must be less than displacement threshold")
        species.append(entry)
    return {"name": name, "thickness_a": float(thickness_a),
            "density_g_cm3": float(density_g_cm3), "species": species}
