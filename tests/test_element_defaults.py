import copy
import unittest

from gsrim.compounds import ELEMENTS, layer_from_compound, layer_from_elements, species_from_element
from gsrim.element_defaults import BINDING_FIELDS, ELEMENT_RECORDS, SOURCES, binding_defaults, binding_hint
from gsrim.project import DEFAULT, validate


class ElementDefaultsTests(unittest.TestCase):
    def test_all_92_elements_have_auditable_records(self):
        self.assertEqual({r['z'] for r in ELEMENT_RECORDS.values()}, set(range(1, 93)))
        self.assertEqual(set(ELEMENTS), set(ELEMENT_RECORDS))
        for symbol, row in ELEMENT_RECORDS.items():
            self.assertGreater(row['mass_u'], 0)
            for field in BINDING_FIELDS:
                self.assertIn(row['sources'][field], SOURCES)
                if row[field] is not None:
                    self.assertGreater(row[field], 0)
            if row['displacement_ev'] is not None:
                self.assertGreater(row['displacement_ev'], row['lattice_ev'])

    def test_reference_samples_and_official_si_tutorial(self):
        self.assertEqual(binding_defaults('H'), dict(zip(BINDING_FIELDS, (10, 3, 2))))
        self.assertEqual(binding_defaults('O'), dict(zip(BINDING_FIELDS, (28, 3, 2))))
        self.assertEqual(binding_defaults('Ga'), dict(zip(BINDING_FIELDS, (25, 3, 2.82))))
        self.assertEqual(binding_defaults('Si'), dict(zip(BINDING_FIELDS, (15, 2, 4.7))))
        self.assertEqual(DEFAULT['layers'][0]['species'][0], species_from_element('Si'))

    def test_paper_table4_is_not_edmin_or_effective_energy_table(self):
        for symbol, expected in {'C':69, 'Ti':30, 'V':57, 'Nb':78, 'Ge':35, 'W':90, 'Au':43}.items():
            self.assertEqual(binding_defaults(symbol)['displacement_ev'], expected)
            self.assertEqual(ELEMENT_RECORDS[symbol]['sources']['displacement_ev'], 'konobeyev2017')

    def test_positive_sublimation_and_missing_values_are_distinguished(self):
        self.assertAlmostEqual(binding_defaults('W')['surface_ev'], 8.68)
        self.assertIsNone(binding_defaults('He')['surface_ev'])
        self.assertIsNone(binding_defaults('He')['displacement_ev'])
        self.assertIn('待填写', binding_hint('He', 'surface_ev'))
        self.assertIn('Assumed', binding_hint('Fe', 'lattice_ev', 'en'))
        p = copy.deepcopy(DEFAULT)
        p['layers'][0]['species'] = [species_from_element('He')]
        with self.assertRaisesRegex(ValueError, 'He.*displacement_ev'):
            validate(p)
        with self.assertRaisesRegex(ValueError, 'He.*unavailable'):
            layer_from_elements([{'symbol':'He', 'amount':1}], 1000, 1)

    def test_explicit_values_and_material_presets_remain_explicit(self):
        layer = layer_from_elements([{'symbol':'He','amount':1, 'displacement_ev':12,
                                     'lattice_ev':1, 'surface_ev':0.2}],1000,1)
        self.assertEqual(layer['species'][0]['displacement_ev'],12)
        self.assertEqual(layer_from_compound('Si')['species'][0], species_from_element('Si'))
        self.assertEqual(layer_from_compound('GaAs')['species'][0]['displacement_ev'],10)
        preset = binding_defaults('Si');preset['displacement_ev'] = 999
        self.assertEqual(binding_defaults('Si')['displacement_ev'],15)


if __name__ == '__main__':
    unittest.main()
