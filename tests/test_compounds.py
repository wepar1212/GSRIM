import unittest

from gsrim.compounds import (
    COMPOUNDS,
    ELEMENTS,
    LAYER_KEYS,
    LAYER_SPECIES_KEYS,
    get_element,
    layer_from_compound,
    layer_from_elements,
    list_compounds,
    list_elements,
)
from gsrim.project import DEFAULT, validate


class CompoundDictionaryTests(unittest.TestCase):
    def test_element_lookup(self):
        si = get_element("Si")
        self.assertEqual(si["z"], 14)
        self.assertAlmostEqual(si["mass_u"], 28.085)
        self.assertEqual(get_element("H")["z"], 1)
        self.assertEqual(get_element("U")["z"], 92)
        with self.assertRaises(KeyError):
            get_element("Xx")

    def test_list_helpers(self):
        elements = list_elements()
        compounds = list_compounds()
        self.assertEqual(elements, sorted(elements))
        self.assertEqual(compounds, sorted(compounds))
        self.assertIn("Si", elements)
        self.assertIn("SiO2", compounds)
        self.assertIn("W", ELEMENTS)
        self.assertIn("U", ELEMENTS)

    def test_required_compounds_present(self):
        required = [
            "Si", "SiO2", "Si3N4", "GaAs", "GaN", "Al2O3", "SiC",
            "Ge", "W", "Cu", "Au", "Al", "Ti", "Fe", "Ni",
            "CH", "Kapton", "H2O", "CH2", "StainlessSteel",
        ]
        for name in required:
            self.assertIn(name, COMPOUNDS)

    def test_sio2_stoichiometry_and_fractions(self):
        layer = layer_from_compound("SiO2", thickness_a=5000)
        symbols = [s["symbol"] for s in layer["species"]]
        self.assertEqual(symbols, ["Si", "O"])
        amounts = [s["amount"] for s in layer["species"]]
        self.assertEqual(amounts, [1.0, 2.0])
        total = sum(amounts)
        fractions = [a / total for a in amounts]
        self.assertAlmostEqual(sum(fractions), 1.0)
        self.assertAlmostEqual(fractions[0], 1.0 / 3.0)
        self.assertAlmostEqual(fractions[1], 2.0 / 3.0)

    def test_layer_from_compound_schema(self):
        for name in list_compounds():
            layer = layer_from_compound(name)
            for key in LAYER_KEYS:
                self.assertIn(key, layer)
            self.assertEqual(sorted(layer), sorted(LAYER_KEYS))
            self.assertTrue(layer["density_g_cm3"] > 0)
            self.assertTrue(layer["thickness_a"] > 0)
            self.assertTrue(1 <= len(layer["species"]) <= 8)
            for species in layer["species"]:
                for key in LAYER_SPECIES_KEYS:
                    self.assertIn(key, species)
                self.assertGreater(species["displacement_ev"], species["lattice_ev"])
                self.assertGreater(species["mass_u"], 0)
                self.assertGreaterEqual(species["z"], 1)
                self.assertGreaterEqual(species["surface_ev"], 0)

    def test_density_override(self):
        default = layer_from_compound("SiO2")
        custom = layer_from_compound("SiO2", density_override=2.65)
        self.assertAlmostEqual(default["density_g_cm3"], 2.20)
        self.assertAlmostEqual(custom["density_g_cm3"], 2.65)
        self.assertEqual(
            [s["symbol"] for s in custom["species"]],
            [s["symbol"] for s in default["species"]],
        )

    def test_layer_from_elements_validation(self):
        layer = layer_from_elements(
            [
                {"symbol": "Si", "amount": 1, "displacement_ev": 25, "lattice_ev": 3, "surface_ev": 4.7},
                {"symbol": "O", "amount": 2, "displacement_ev": 28, "lattice_ev": 3, "surface_ev": 2.0},
            ],
            thickness_a=20000,
            density_g_cm3=2.2,
            name="Thermal oxide",
        )
        self.assertEqual(layer["name"], "Thermal oxide")
        self.assertEqual(layer["species"][0]["z"], 14)
        self.assertEqual(layer["species"][1]["z"], 8)
        self.assertAlmostEqual(layer["species"][1]["mass_u"], 15.999)
        with self.assertRaises(ValueError):
            layer_from_elements([], 1000, 2.0)
        with self.assertRaises(ValueError):
            layer_from_elements([{"symbol": "Si", "amount": 1}], -1, 2.0)
        with self.assertRaises(ValueError):
            layer_from_elements([{"symbol": "Si", "amount": 1}], 1000, 0)
        with self.assertRaises(ValueError):
            layer_from_elements(
                [{"symbol": "Si", "amount": 1, "displacement_ev": 3, "lattice_ev": 3}],
                1000,
                2.0,
            )
        with self.assertRaises(ValueError):
            layer_from_elements(
                [
                    {"symbol": "Si", "amount": 1},
                    {"symbol": "Si", "amount": 1},
                ],
                1000,
                2.0,
            )

    def test_layer_integrates_with_project_schema(self):
        layer = layer_from_compound("SiO2", thickness_a=2000)
        project = dict(DEFAULT)
        project["layers"] = [layer]
        _, target = validate(project)
        self.assertEqual(len(target.layers), 1)
        self.assertEqual(len(target.layers[0].species), 2)
        self.assertAlmostEqual(sum(target.layers[0].fractions), 1.0)

    def test_unknown_compound(self):
        with self.assertRaises(KeyError):
            layer_from_compound("Unobtainium")

    def test_aliases(self):
        self.assertEqual(layer_from_compound("water")["name"], "H2O")
        self.assertEqual(layer_from_compound("Kapton")["name"], "Kapton")
        self.assertEqual(layer_from_compound("stainless steel")["name"], "StainlessSteel")
        self.assertEqual(layer_from_compound("photoresist")["name"], "CH")


if __name__ == "__main__":
    unittest.main()
