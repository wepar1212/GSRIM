import unittest
import numpy as np
from scipy.integrate import quad
from gsrim.scattering import scatter, phi, screening_length, COULOMB_EV_ANGSTROM


class ScatteringTests(unittest.TestCase):
    def test_rutherford_limit(self):
        e = np.geomspace(10, 1e6, 20)
        b = np.geomspace(1e-3, 10, 20)
        theta, transfer, _ = scatter(e, b, z1=2, z2=14, m1=4, m2=28, screened=False)
        expected = 2*np.arctan(COULOMB_EV_ANGSTROM*28/(2*(e*28/32)*b))
        np.testing.assert_allclose(theta, expected, atol=2e-7, rtol=2e-6)
        self.assertTrue(np.all((transfer >= 0) & (transfer <= e)))

    def test_head_on_equal_mass(self):
        theta, transfer, _ = scatter([100, 10000], 0, z1=14, z2=14, m1=28, m2=28)
        np.testing.assert_allclose(theta, np.pi)
        np.testing.assert_allclose(transfer, [100, 10000])

    def test_screened_against_adaptive_integral(self):
        for energy, b in [(100, .01), (1000, .2), (100000, .05)]:
            theta, _, root = scatter(energy, b, z1=2, z2=14, m1=4, m2=28)
            a = screening_length(2, 14)
            ec = energy*28/32
            def integrand(t):
                u = 1-t*t
                f = 1-(b*u/root)**2 - COULOMB_EV_ANGSTROM*28*u/root*phi(root/u/a)/ec
                return 2*t/np.sqrt(f)
            value, _ = quad(integrand, 0, 1, epsabs=1e-10)
            self.assertAlmostEqual(float(theta), np.pi-2*b/root*value, places=7)

    def test_invalid_inputs(self):
        for e, b in [(0, 1), (-1, 1), (100, -1), (np.nan, 1)]:
            with self.assertRaises(ValueError):
                scatter(e, b, z1=2, z2=14, m1=4, m2=28)

    def test_quadrature_convergence(self):
        b = np.geomspace(.001, 1, 30)
        args = dict(z1=1, z2=14, m1=1, m2=28)
        first = scatter(10000, b, order=64, **args)[0]
        second = scatter(10000, b, order=256, **args)[0]
        np.testing.assert_allclose(first, second, atol=2e-6)


if __name__ == "__main__":
    unittest.main()
