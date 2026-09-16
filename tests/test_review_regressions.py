import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from gsrim.project import DEFAULT
from gsrim.iaea_stopping import StoppingSeries, ELEMENT_DENSITY, ATOMIC_MASS, bragg_compound
from gsrim.se_tables import se_for_pair, default_energy_grid
from gsrim.electronic_stopping import bethe_bloch_rustbca_style
from gsrim.simulation import Simulation, NREC, ENGINE_REVISION


class ReviewRegressions(unittest.TestCase):
    def index(self):
        e=np.array([1e3,1e4,1e5,1e6])
        return {('O',sym):StoppingSeries('O',sym,e,np.array([1.,2.,3.,4.])*factor,4,('synthetic unit test',))
                for sym,factor in [('Si',10.),('O',.1)]}

    def test_density_scaling_element_and_compound(self):
        with patch('gsrim.se_tables.iaea_index',return_value=self.index()):
            for species in [[('Si',14,28.085,1.)],[('Si',14,28.085,1/3),('O',8,15.999,2/3)]]:
                vals=[]
                for rho,n in [(2.2,.06),(4.4,.12)]:
                    se,_=se_for_pair('O',8,15.999,species,n,rho,np.array([1e4,1e5]),'iaea')
                    vals.append(se)
                np.testing.assert_allclose(vals[1],2*vals[0],rtol=1e-12)

    def test_bragg_uses_per_atom_cross_sections(self):
        idx=self.index();fractions=[('Si',1/3),('O',2/3)];density=.066
        mixed=bragg_compound(idx,'O',fractions,[ELEMENT_DENSITY[s] for s,_ in fractions],number_density_a3=density)
        # Endpoints are common to both grids, so interpolation introduces no ambiguity.
        expected=sum(f*idx['O',sym].se_ev_a[0]/(ELEMENT_DENSITY[sym]*6.02214076e23/ATOMIC_MASS[sym]/1e24)
                     for sym,f in fractions)*density
        self.assertAlmostEqual(mixed.se_ev_a[0],expected)

    def test_iaea_high_and_low_fallback(self):
        e=np.array([100.,10000.,1e6,2e6,1e7])
        with patch('gsrim.se_tables.iaea_index',return_value=self.index()):
            args=('O',8,15.999,[('Si',14,28.085,1.)],.05,2.329,e)
            actual,source=se_for_pair(*args,model='iaea')
            fallback,_=se_for_pair(*args,model='biersack-varelas')
            np.testing.assert_allclose(actual[[0,3,4]],fallback[[0,3,4]])
            np.testing.assert_allclose(actual[[1,2]],[20.,40.])
            self.assertIn('fallback_nodes=3/5',source)

    def test_nist_high_and_low_fallback(self):
        e=np.array([100.,1e4,1e5,1e7])
        with patch('gsrim.se_tables.iaea_index',return_value={}),patch('gsrim.se_tables.get_se_series',return_value=(np.array([1e3,1e4,1e5]),np.array([1.,2.,3.]))):
            args=('He',2,4.0026,[('Si',14,28.085,1.)],.05,2.329,e)
            actual,_=se_for_pair(*args,model='iaea')
            expected,_=se_for_pair(*args,model='biersack-varelas')
            np.testing.assert_allclose(actual[[0,3]],expected[[0,3]])
            np.testing.assert_allclose(actual[[1,2]],[2.,3.])

    def test_bethe_charge_scaling_same_velocity(self):
        h=bethe_bloch_rustbca_style(1,14,1e6,1,.05)
        o=bethe_bloch_rustbca_style(8,14,16e6,16,.05)
        self.assertAlmostEqual(float(o/h),64.)

    def test_bethe_reference_equation(self):
        z1,z2,e,m,n=2,14,1e6,4.,.05
        ratio=e/(m*931.494061e6);beta2=ratio*(2+ratio)/(1+ratio)**2
        i=z2*(9.76+58.5*z2**-1.19);eb=2*510998.95*beta2/i
        expected=4*np.pi*14.3996454784255**2*n*z2*z1**2/(510998.95*beta2)*np.log(eb+1+5/eb)
        self.assertAlmostEqual(float(bethe_bloch_rustbca_style(z1,z2,e,m,n)),expected)

    def populated(self,failed=False,sputter=False):
        p=copy.deepcopy(DEFAULT);p['run']['ions']=2
        s=Simulation(p);s.completed=2;s.status='completed'
        r=np.zeros((2,NREC));r[:,0]=0;r[:,3]=[100.,1900.];r[1,16]=int(failed);r[0,13]=int(sputter)
        s.records=[r];s.hist[0,0]=1;s.hist[0,-1]=1
        return s

    def test_failed_results_disable_dose(self):
        snap=self.populated(failed=True).snapshot()
        self.assertTrue(snap['diagnostic_only'])
        self.assertIsNone(snap['stats']['peak_per_cm'])
        self.assertIsNone(snap['stats']['mean_range_nm'])
        self.assertEqual(snap['stats']['failed_histories'],1)

    def test_kp_not_fabricated_from_transfer(self):
        s=self.populated();s.records[0][:,12]=1e6
        stats=s.snapshot()['stats']
        self.assertIsNone(stats['damage_energy_ev_per_ion'])
        self.assertIsNone(stats['kinchin_pease_vacancies_per_ion'])
        self.assertEqual(stats['cumulative_displacing_transfer_ev_per_ion'],1e6)
        p=copy.deepcopy(DEFAULT);p['run']['damage']='kinchin-pease'
        with self.assertRaisesRegex(ValueError,'KP'):Simulation(p).start()

    def test_spectral_axes_independent(self):
        s=self.populated();s.project['ion']['energy_kev']=40
        snap=s.snapshot();axes=snap['spectra_axes_ev']
        np.testing.assert_allclose(axes['backscattered'],np.array(axes['sputtered'])*40)
        np.testing.assert_array_equal(axes['backscattered'],axes['transmitted'])

    def test_current_checkpoint_and_sputtering(self):
        s=self.populated(sputter=True)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.npz';s.save_checkpoint(path)
            restored=Simulation.load_checkpoint(path)
            self.assertEqual(restored.engine_revision,ENGINE_REVISION)
            self.assertEqual(restored.snapshot()['stats']['failed_histories'],0)
            self.assertFalse(restored.snapshot()['diagnostic_only'])

    def test_legacy_cannot_resume(self):
        s=self.populated();s.engine_revision=1;s.project['run']['ions']=3
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.npz';s.save_checkpoint(path)
            restored=Simulation.load_checkpoint(path)
            self.assertTrue(restored.snapshot()['diagnostic_only'])
            with self.assertRaisesRegex(ValueError,'Legacy'):restored.start()


@unittest.skipUnless(os.environ.get('GSRIM_TEST_GPU')=='1','GPU tests not requested')
class GPUReviewRegressions(unittest.TestCase):
    def test_tiny_flight_has_no_interpolation_energy_loss(self):
        p=copy.deepcopy(DEFAULT)
        grid=default_energy_grid(3,1e6,320);i=np.searchsorted(grid,50000)-1
        p['ion']['energy_kev']=float((grid[i]+grid[i+1])/2000)
        p['layers'][0]['thickness_a']=1e-6
        p['run'].update(ions=4,batch_size=4,mode='ions')
        s=Simulation(p);s.start();s.thread.join(30)
        self.assertEqual(s.status,'completed',s.error)
        stats=s.snapshot()['stats']
        self.assertEqual(stats['transmitted'],4)
        self.assertLess(stats['electronic_ev_per_ion'],1e-3)
