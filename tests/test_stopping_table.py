import os
import unittest
import numpy as np
from gsrim.scatter_table import build_universal_table, interpolate, EPS_MIN, EPS_MAX, RHO_MIN, RHO_MAX, _theta_quadrature
from gsrim.scattering import scatter, screening_length, COULOMB_EV_ANGSTROM
from gsrim.electronic_stopping import (
    lindhard_scharff_coefficient, bethe_stopping, mean_excitation_energy,
    MEAN_EXCITATION_EV, _LS_FRONT,
)


class StoppingTests(unittest.TestCase):
    def test_ls_constant_near_derived_value(self):
        # Derived front factor is ~1.210, literature often quotes 1.212.
        self.assertGreater(_LS_FRONT, 1.20)
        self.assertLess(_LS_FRONT, 1.22)

    def test_ls_he_si_scale(self):
        n_si = 2.329 * 6.02214076e23 / 28.085 / 1e24  # A^-3
        k = lindhard_scharff_coefficient(2, 14, 4.0026, n_si)
        se5 = k * np.sqrt(5000.0)
        # Published LS-scale for 5 keV He in Si is a few eV/A.
        self.assertGreater(se5, 1.0)
        self.assertLess(se5, 8.0)

    def test_bethe_positive_high_energy(self):
        n_si = 2.329 * 6.02214076e23 / 28.085 / 1e24
        se = bethe_stopping(2, 4.0026, 1.0e6, n_si, 14.0, MEAN_EXCITATION_EV[14])
        self.assertTrue(np.isfinite(se) and se > 0)

    def test_mean_excitation_brugg(self):
        i = mean_excitation_energy([14, 8], [1, 2])
        self.assertGreater(i, 100)
        self.assertLess(i, 200)


class ScatterTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tab = build_universal_table(eps_nodes=256, rho_nodes=256, quad_order=32)

    def test_reduced_matches_lab(self):
        z1,z2,m1,m2 = 2,14,4.0026,28.085
        rng = np.random.default_rng(1)
        E = np.exp(rng.uniform(np.log(50), np.log(1e5), 200))
        b = np.exp(rng.uniform(np.log(1e-3), np.log(1.0), 200))
        a = screening_length(z1,z2)
        k = COULOMB_EV_ANGSTROM*z1*z2
        eps = E*m2/(m1+m2)*a/k
        rho = b/a
        mask = (eps>=EPS_MIN)&(eps<=EPS_MAX)&(rho>=RHO_MIN)&(rho<=RHO_MAX)
        ang,_,_ = scatter(E,b,z1=z1,z2=z2,m1=m1,m2=m2,engine='cpu',order=64)
        red = _theta_quadrature(eps[mask], rho[mask], order=48)
        np.testing.assert_allclose(red, ang[mask], atol=1e-6, rtol=1e-6)

    def test_table_interpolation_accuracy(self):
        z1,z2,m1,m2 = 2,14,4.0026,28.085
        rng = np.random.default_rng(2)
        E = np.exp(rng.uniform(np.log(20), np.log(2e5), 400))
        b = np.exp(rng.uniform(np.log(1e-3), np.log(2.0), 400))
        a = screening_length(z1,z2)
        k = COULOMB_EV_ANGSTROM*z1*z2
        eps = np.clip(E*m2/(m1+m2)*a/k, EPS_MIN, EPS_MAX)
        rho = np.clip(b/a, RHO_MIN, RHO_MAX)
        mask = (E*m2/(m1+m2)*a/k>=EPS_MIN)&(E*m2/(m1+m2)*a/k<=EPS_MAX)&(b/a>=RHO_MIN)&(b/a<=RHO_MAX)
        ang,_,_ = scatter(E,b,z1=z1,z2=z2,m1=m1,m2=m2,engine='cpu',order=64)
        th = interpolate(self.tab['theta'], self.tab['log_eps'], self.tab['log_rho'], eps, rho)
        err = np.abs(th[mask]-ang[mask])
        # 256^2 bilinear: keep a loose but meaningful bound; bicubic on GPU is tighter.
        self.assertLess(np.median(err), 5e-3)
        self.assertLess(np.percentile(err, 99), 2e-2)


@unittest.skipUnless(os.environ.get('GSRIM_TEST_GPU')=='1','GPU tests not requested')
class TableTransportTests(unittest.TestCase):
    def test_table_mode_completes_and_conserves(self):
        from gsrim.project import DEFAULT, validate
        from gsrim.simulation import Simulation
        import copy
        p = copy.deepcopy(DEFAULT)
        p['run']['ions'] = 64
        p['run']['batch_size'] = 64
        p['physics']['scattering'] = 'table'
        s = Simulation(p)
        s.start(); s.thread.join(60)
        self.assertEqual(s.status, 'completed', s.error)
        stats = s.snapshot()['stats']
        self.assertLess(stats['max_energy_error_ev'], 1e-5)
        self.assertEqual(stats['implanted']+stats['backscattered']+stats['transmitted'], 64)
        self.assertIsNotNone(stats.get('lateral_rms_nm'))

    def test_quadrature_mode_still_available(self):
        from gsrim.project import DEFAULT
        from gsrim.simulation import Simulation
        from unittest.mock import patch
        import copy
        p = copy.deepcopy(DEFAULT)
        p['run']['ions'] = 8
        p['run']['batch_size'] = 8
        p['physics']['scattering'] = 'quadrature'
        s = Simulation(p)
        # Direct quadrature must work even when no scattering table is available.
        with patch('gsrim.simulation.load_cached_or_build', side_effect=OSError('Table cache unavailable')):
            s.start(); s.thread.join(90)
        self.assertFalse(s.thread.is_alive())
        self.assertEqual(s.status, 'completed', s.error)
        self.assertLess(s.snapshot()['stats']['max_energy_error_ev'], 1e-5)


if __name__ == '__main__':
    unittest.main()
