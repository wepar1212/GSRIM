import unittest
import numpy as np
from gsrim.materials import Species, Layer, Target
from gsrim.stopping import ElectronicStoppingTable


class MaterialTests(unittest.TestCase):
    def setUp(self):
        self.si=Species("Si",14,28.085,25,3,4.7)
        self.layer=Layer(1000,2.329,(self.si,),(1,))

    def test_density_units(self):
        self.assertAlmostEqual(self.layer.number_density_a3,.04994,places=4)

    def test_stoichiometry(self):
        oxygen=Species("O",8,15.999,28,3,2)
        layer=Layer(1000,2.2,(self.si,oxygen),(1,2))
        np.testing.assert_allclose(layer.fractions,[1/3,2/3])

    def test_layer_boundaries(self):
        target=Target((self.layer,self.layer))
        self.assertEqual([target.locate(z) for z in [-1,0,999.9,1000,1999.9,2000]],
                         [-1,0,0,1,1,2])

    def test_invalid_material(self):
        with self.assertRaises(ValueError):
            Layer(1000,0,(self.si,),(1,))
        with self.assertRaises(ValueError):
            Layer(1000,2.3,(self.si,self.si),(1,1))

    def test_stopping_interpolation(self):
        # Synthetic power law is only a numerical test, not a physical database.
        table=ElectronicStoppingTable(1,"test",(100,10000),(1,10),"synthetic unit test")
        self.assertAlmostEqual(float(table.evaluate(1000)),np.sqrt(10))
        for energy in [0,99,10001,np.nan]:
            with self.assertRaises(ValueError):
                table.evaluate(energy)

    def test_stopping_requires_source(self):
        with self.assertRaises(ValueError):
            ElectronicStoppingTable(1,"test",(1,2),(1,2),"")
