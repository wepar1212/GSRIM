"""Versioned project schema shared by the GUI and simulation engine."""
import copy
import math
from .materials import Species, Layer, Target
from .compounds import species_from_element

DEFAULT = {
    "schema": 1, "name": "He in Si — development example",
    "ion": {"symbol": "He", "z": 2, "mass_u": 4.0026, "energy_kev": 5, "angle_deg": 0},
    "layers": [{"name": "Layer1", "thickness_a": 2000, "density_g_cm3": 2.329,
        "species": [species_from_element("Si")]}],
    "run": {"ions": 256, "seed": 12345, "batch_size": 4096, "bins": 160,
            "cutoff_ev": 3, "max_events": 100000, "mode": "cascades", "impact_scale": 1.0,
            "damage": "creation"},
    "physics": {"stopping": "iaea", "scattering": "table", "validated": False},
}


def validate(project):
    p=copy.deepcopy(project)
    if p.get("schema") != 1:
        raise ValueError("Unsupported project schema")
    if not isinstance(p.get("name"), str) or len(p["name"]) > 200:
        raise ValueError("Project name must contain at most 200 characters")
    ion=p["ion"]
    Species(ion["symbol"],ion["z"],ion["mass_u"],1,0,0)
    for key in ("energy_kev", "angle_deg"):
        if not math.isfinite(ion[key]):
            raise ValueError("Nonfinite ion parameter")
    if not 0.01 <= ion["energy_kev"] <= 25000*ion["mass_u"]:
        raise ValueError("Energy must be 0.01 keV to 25 MeV/u; extreme energies need dedicated stopping models")
    if not 0 <= ion["angle_deg"] < 89.9:
        raise ValueError("Incidence angle must be in [0, 89.9) degrees from normal")
    if not 1 <= len(p["layers"]) <= 8:
        raise ValueError("Use 1..8 layers")
    layers=[]
    all_species={}
    for layer in p["layers"]:
        if not 1 <= len(layer["species"]) <= 8:
            raise ValueError("Use 1..8 species per layer")
        items=[]
        for s in layer["species"]:
            for key in ("displacement_ev", "lattice_ev", "surface_ev"):
                if s.get(key) is None or s.get(key) == "":
                    raise ValueError(f"{s.get('symbol', '?')}: {key} is unavailable; enter a material-specific value")
            item=Species(**{key:s[key] for key in ("symbol","z","mass_u","displacement_ev","lattice_ev","surface_ev")})
            if item.lattice_ev >= item.displacement_ev:
                raise ValueError("Lattice binding energy must be less than displacement threshold")
            # Current GPU state uses a globally unique species identity.
            if item.z in all_species and all_species[item.z] != item:
                raise ValueError("Same element must have consistent mass and binding parameters across layers")
            all_species[item.z]=item
            items.append(item)
        layers.append(Layer(layer["thickness_a"],layer["density_g_cm3"],tuple(items),
                            tuple(s["amount"] for s in layer["species"])))
    if len(all_species)>15:
        raise ValueError("At most 15 distinct target species")
    if p.get("physics",{}).get("stopping") not in ("lindhard-scharff","bethe","blend","iaea","biersack-varelas","auto"):
        raise ValueError("Unknown electronic stopping model")
    if p.get("physics",{}).get("scattering","table") not in ("table","quadrature"):
        raise ValueError("scattering must be table or quadrature")
    p.setdefault("physics",{})["scattering"]=p["physics"].get("scattering","table")
    run=p["run"]
    limits={"ions":(1,1000000),"seed":(0,2147483647),"batch_size":(1,65536),
            "bins":(20,2000),"max_events":(100,500000)}
    for name,(low,high) in limits.items():
        if type(run[name]) is not int or not low <= run[name] <= high:
            raise ValueError(f"{name} must be an integer in [{low}, {high}]")
    if not math.isfinite(run["cutoff_ev"]) or not 0.1 <= run["cutoff_ev"] <= 100:
        raise ValueError("Cutoff must be 0.1..100 eV")
    if run["cutoff_ev"] >= ion["energy_kev"]*1000:
        raise ValueError("Cutoff must be below initial energy")
    if not math.isfinite(run["impact_scale"]) or not .5 <= run["impact_scale"] <= 2:
        raise ValueError("Impact scale must be 0.5..2; convergence must be checked")
    if run["mode"] not in ("cascades","ions"):
        raise ValueError("Unknown mode")
    if run.get("damage","creation") not in ("creation","kinchin-pease"):
        raise ValueError("damage must be creation or kinchin-pease")
    p["physics"]["validated"]=False
    return p,Target(tuple(layers))
