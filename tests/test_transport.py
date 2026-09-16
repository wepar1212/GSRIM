import copy
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
from gsrim.project import DEFAULT,validate
from gsrim.simulation import Simulation


class ProjectTests(unittest.TestCase):
    def test_default(self):validate(DEFAULT)

    def test_bad_energy_and_nan(self):
        for energy in (float('nan'),0,1e9):
            p=copy.deepcopy(DEFAULT);p['ion']['energy_kev']=energy
            with self.assertRaises(ValueError):validate(p)

    def test_zero_stoichiometry(self):
        p=copy.deepcopy(DEFAULT);p['layers'][0]['species'][0]['amount']=0
        with self.assertRaises(ValueError):validate(p)

    def test_invalid_stop_model(self):
        p=copy.deepcopy(DEFAULT);p['physics']['stopping']='invented'
        with self.assertRaises(ValueError):validate(p)


@unittest.skipUnless(os.environ.get('GSRIM_TEST_GPU')=='1','GPU tests not requested')
class TransportTests(unittest.TestCase):
    def run_case(self,project):
        s=Simulation(project);s.start();s.thread.join(40)
        self.assertFalse(s.thread.is_alive(),'Run exceeded test time budget')
        self.assertEqual(s.status,'completed',s.error)
        return s

    def small(self):
        p=copy.deepcopy(DEFAULT);p['run']['ions']=12;p['run']['batch_size']=4
        return p

    def test_energy_population_normalization(self):
        s=self.run_case(self.small());snapshot=s.snapshot();stats=snapshot['stats']
        self.assertEqual(stats['implanted']+stats['backscattered']+stats['transmitted'],12)
        self.assertLess(stats['max_energy_error_ev'],1e-6)
        width=s.target.thickness_a/s.project['run']['bins']*1e-8
        self.assertAlmostEqual(sum(snapshot['implant_per_cm'])*width,stats['implanted']/12)
        self.assertAlmostEqual(sum(s.hist[1])/12,stats['electronic_ev_per_ion'])
        self.assertAlmostEqual(sum(s.hist[2])/12,stats['lattice_ev_per_ion'])

    def test_batch_size_independent_histories(self):
        p=self.small();first=self.run_case(p)
        p['run']['batch_size']=12;second=self.run_case(p)
        np.testing.assert_array_equal(np.concatenate(first.records),np.concatenate(second.records))
        np.testing.assert_allclose(first.hist,second.hist,atol=1e-8)

    def test_checkpoint_resume(self):
        p=self.small();full=self.run_case(p)
        p['run']['ions']=4;part=self.run_case(p)
        part.project['run']['ions']=12
        with tempfile.TemporaryDirectory(prefix='gsrim-test-') as folder:
            path=Path(folder)/'checkpoint.npz';part.save_checkpoint(path)
            resumed=Simulation.load_checkpoint(path);resumed.start();resumed.thread.join(40)
            self.assertEqual(resumed.status,'completed',resumed.error)
            np.testing.assert_array_equal(np.concatenate(full.records),np.concatenate(resumed.records))
            np.testing.assert_allclose(full.hist,resumed.hist,atol=1e-8)

    def test_thin_target_transmission(self):
        p=self.small();p['layers'][0]['thickness_a']=.001
        s=self.run_case(p)
        self.assertEqual(s.snapshot()['stats']['transmitted'],12)

    def test_identical_layers_preserve_statistics_not_paths(self):
        # Crossing resamples an exponential free flight; only conservation is exact.
        p=self.small();p['layers'][0]['thickness_a']=1000
        p['layers'].append(copy.deepcopy(p['layers'][0]));s=self.run_case(p)
        self.assertLess(s.snapshot()['stats']['max_energy_error_ev'],1e-6)

    def test_ion_only_has_no_sputter(self):
        p=self.small();p['run']['mode']='ions';s=self.run_case(p)
        self.assertEqual(s.snapshot()['stats']['sputter_yield_front'],0)

    def test_limit_failure_is_explicit(self):
        p=self.small();p['run']['max_events']=100
        s=Simulation(p);s.start();s.thread.join(40)
        self.assertEqual(s.status,'error')
        self.assertGreater(s.snapshot()['stats']['failed_histories'],0)

    def test_pause_then_resume(self):
        p=self.small();s=Simulation(p);s.start();s.pause();s.thread.join(40)
        self.assertEqual(s.status,'paused')
        s.start();s.thread.join(40);self.assertEqual(s.status,'completed',s.error)

    def test_srim_like_stats_fields(self):
        p=self.small()
        s=self.run_case(p);stats=s.snapshot()['stats']
        for key in ('vacancies_per_ion','kinchin_pease_vacancies_per_ion','mean_range_a',
                    'lateral_proj_a','radial_a','energy_loss_percent','ionization_ev_per_ion'):
            self.assertIn(key,stats)
        self.assertGreater(stats['energy_loss_percent']['ions']['ionization'],0)
        self.assertIsNotNone(stats['mean_range_a'])
        self.assertIsNone(stats['kinchin_pease_vacancies_per_ion'])
