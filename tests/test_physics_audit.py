"""Physics invariants and unit conversions; these are not experimental fits."""
import copy
import csv
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from gsrim.compounds import ELEMENTS, species_from_element
from gsrim.element_defaults import ELEMENT_RECORDS
from gsrim.electronic_stopping import bethe_stopping, mean_excitation_energy, MEAN_EXCITATION_EV
from gsrim.iaea_stopping import energy_to_ev, load_index, build_series, StoppingSeries
from gsrim.materials import Species, Layer, Target
from gsrim.nist_stopping import get_se_series
from gsrim.project import DEFAULT, validate
from gsrim.scatter_table import build_universal_table, interpolate, _theta_quadrature
from gsrim.scattering import scatter, screening_length, COULOMB_EV_ANGSTROM
from gsrim.se_tables import se_for_pair, build_tau
from gsrim.simulation import Simulation, ENGINE_REVISION


class AuditPhysicsTests(unittest.TestCase):
    def test_all_energy_units_preserve_same_velocity(self):
        for unit,value in [('MeV/u',.01),('keV/u',10),('eV/u',10000),
                           ('MeV',.04),('keV',40),('eV',40000)]:
            self.assertAlmostEqual(energy_to_ev(value,unit,'He','4'),40026.)
        with self.assertRaises(ValueError):energy_to_ev(1,'unrecognized','He','4')
        with self.assertRaises(ValueError):energy_to_ev(1,'MeV/u','Xx','')

    def test_iaea_csv_respects_each_row_unit(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'units.csv'
            fields=['projectile_name','ion_isotope','target_name','energy','energy_unit',
                    'stopping_power_converted','stopping_unit_converted']
            with path.open('w',newline='') as f:
                w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
                for unit,scale in [('MeV/u',.01),('keV/u',10),('MeV',.04),('keV',40)]:
                    for factor in (1,2,3,4):
                        w.writerow(dict(zip(fields,['He','4','Si',scale*factor,unit,1,'MeV/(mg/cm2)'])))
                w.writerow(dict(zip(fields,['He','4','Si',1,'wrong',1,'MeV/(mg/cm2)'])))
            index=load_index(path)
            np.testing.assert_allclose(index['He','Si'].energy_ev,40026*np.arange(1,5))
            np.testing.assert_allclose(index['He','Si'].se_ev_a,23.29)

    def test_iaea_isotope_axis_changes_with_projectile_mass(self):
        series=StoppingSeries('He','Si',np.array([4.,8.,12.,16.])*1e4,np.ones(4),4,('synthetic',))
        actual=build_series({('He','Si'):series},'He','Si',projectile_mass_u=3.)
        np.testing.assert_allclose(actual.energy_ev,series.energy_ev*3/4.0026)

    def test_nist_isotope_scaling_and_mass_stopping_units(self):
        energies=np.array([1e4,1e5]);losses=np.array([2.,3.])
        e,se=get_se_series('H','Si',2.329,{('H','Si'):(energies,losses)},projectile_mass_u=2.014)
        np.testing.assert_allclose(e,energies*2.014/1.007276466621)
        np.testing.assert_allclose(se,losses*2.329*.01)

    def test_bv_compound_obeys_elementwise_bragg_additivity(self):
        e=np.geomspace(1,1e8,48)
        for composition in [[('O',8,15.999,.6),('Ga',31,69.723,.4)],
                            [('H',1,1.008,.9),('U',92,238.02891,.1)]]:
            actual,_=se_for_pair('He',2,4.0026,composition,.05,3.,e,'biersack-varelas')
            expected=sum(f*se_for_pair('He',2,4.0026,[(sym,z,m,1.)],.05,3.,e,'biersack-varelas')[0]
                         for sym,z,m,f in composition)
            np.testing.assert_allclose(actual,expected,rtol=1e-12)

    def test_bethe_bare_charge_squared_at_same_speed(self):
        h=bethe_stopping(1,1.,1e6,.05,14.,173.)
        he=bethe_stopping(2,4.,4e6,.05,14.,173.)
        self.assertAlmostEqual(float(he/h),4.)

    def test_bragg_mean_excitation_uses_electron_fractions(self):
        expected=np.exp((14*np.log(MEAN_EXCITATION_EV[14])+16*np.log(MEAN_EXCITATION_EV[8]))/30)
        self.assertAlmostEqual(mean_excitation_energy([14,8],[1,2]),expected)

    def test_all_92_element_identities_and_missing_default_guards(self):
        for symbol,record in ELEMENT_RECORDS.items():
            Species(symbol,record['z'],record['mass_u'],10,1,0)
            p=copy.deepcopy(DEFAULT);p['layers'][0]['species']=[species_from_element(symbol)]
            if any(p['layers'][0]['species'][0][k] is None for k in ('displacement_ev','lattice_ev','surface_ev')):
                with self.assertRaisesRegex(ValueError,'unavailable'):validate(p)
            else:validate(p)
        p=copy.deepcopy(DEFAULT);p['ion']['z']=92
        with self.assertRaisesRegex(ValueError,'symbol'):validate(p)

    def test_unrepresentable_layer_and_stoichiometry_rejected(self):
        s=Species('Si',14,28.085,15,2,4.7)
        with self.assertRaises(ValueError):Target((Layer(1e4,2.,(s,),(1,)),Layer(1e-20,2.,(s,),(1,))))
        with self.assertRaises(ValueError):Layer(1,2.,(s,Species('O',8,15.999,28,3,2)),(1e308,1e308))

    def test_path_primitive_rejects_invalid_tables(self):
        for e,s in [([2,1],[1,1]),([1,2],[0,1]),([1,2],[1,np.nan])]:
            with self.assertRaises(ValueError):build_tau(e,s)

    def test_near_coulomb_zbl_turning_point_has_valid_bracket(self):
        # At eps=1e6, rho=1e-6 the rounded phi(0)>1 matters. The
        # independently implemented laboratory solver must remain physical.
        a=screening_length(1,1);k=COULOMB_EV_ANGSTROM
        eps=1e6;rho=1e-6
        angle,transfer,_=scatter(2*eps*k/a,rho*a,z1=1,z2=1,m1=1,m2=1)
        self.assertGreater(float(angle),.92);self.assertLess(float(angle),.94)
        self.assertGreater(float(transfer),0)

    def test_positive_first_impact_column_is_not_forced_head_on(self):
        tab=build_universal_table(12,12,eps_range=(1e4,1e8),rho_range=(1e-6,1),quad_order=64)
        self.assertLess(tab['theta'][-1,0],.011)
        self.assertAlmostEqual(float(interpolate(tab['theta'],tab['log_eps'],tab['log_rho'],1e8,0)),np.pi)
        with self.assertRaises(ValueError):interpolate(tab['theta'],tab['log_eps'],tab['log_rho'],1,1)

    def test_version_two_cannot_resume_into_corrected_physics(self):
        sim=Simulation(copy.deepcopy(DEFAULT));sim.engine_revision=2
        self.assertGreater(ENGINE_REVISION,2)
        with self.assertRaisesRegex(ValueError,'Legacy'):sim.start()


@unittest.skipUnless(os.environ.get('GSRIM_TEST_GPU')=='1','GPU tests not requested')
class AuditGPUPhysicsTests(unittest.TestCase):
    def test_sub_nanometer_layers_do_not_get_skipped_by_position_nudge(self):
        p=copy.deepcopy(DEFAULT);p['run'].update(ions=4,batch_size=4,mode='ions')
        p['layers'][0]['thickness_a']=1e-12
        p['layers'].append(copy.deepcopy(p['layers'][0]))
        with tempfile.TemporaryDirectory() as folder:
            sim=Simulation(p,checkpoint_path=Path(folder)/'check.npz')
            sim.start();sim.thread.join(60)
            self.assertEqual(sim.status,'completed',sim.error)
            self.assertEqual(sim.snapshot()['stats']['transmitted'],4)
            self.assertLess(sim.snapshot()['stats']['max_energy_error_ev'],1e-5)
