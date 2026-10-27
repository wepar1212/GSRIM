import copy
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np

from gsrim.output import export_bundle, plot_from_snapshot, read_reference_table, reference_plots, text_outputs
from gsrim.project import DEFAULT
from gsrim.simulation import DETAIL_CHANNELS, NREC, Simulation


def populated():
    p=copy.deepcopy(DEFAULT);p["run"].update(ions=2,bins=20)
    sim=Simulation(p);sim.completed=2;sim.status="completed"
    r=np.zeros((2,NREC));r[:,0]=0;r[:,3]=[100,200];r[:,18]=[0,1]
    sim.records=[r];sim.hist[0,:2]=1
    sim.detail_hist[0,0]=60;sim.detail_hist[1,0]=20;sim.hist[1,0]=80
    sim.detail_hist[2,0]=10;sim.detail_hist[3,0]=6;sim.hist[2,0]=16
    sim.detail_hist[7,0]=4;sim.hist[4,0]=4
    sim.detail_hist[8,0]=6;sim.hist[3,0]=6
    return sim


class OutputTests(unittest.TestCase):
    def test_range_units_integrate_to_implanted_fraction(self):
        state=populated().snapshot();data=plot_from_snapshot(state,"range")
        width=100
        self.assertAlmostEqual(sum(data.series[0][1])*width*1e-8,1.)
        self.assertAlmostEqual(sum(data.series[1][1])*width*1e-8,2.)

    def test_split_energy_density_integrates_to_energy_per_ion(self):
        state=populated().snapshot()
        for mode,key in [("ionization","electronic_ev"),("phonons","lattice_ev")]:
            plot=plot_from_snapshot(state,mode)
            integral=sum(sum(s[1]) for s in plot.series)*100
            self.assertAlmostEqual(integral,sum(state["profiles"][key]))

    def test_export_aligned_numeric_table_and_no_false_vacancies(self):
        sim=populated();output=text_outputs(sim.snapshot(),np.concatenate(sim.records))
        with tempfile.TemporaryDirectory() as folder:
            for name in ("RANGE.txt","IONIZ.txt","PHONON.txt","DISPLACEMENTS.txt"):
                path=Path(folder)/name;path.write_text(output[name],encoding="utf-8")
                data=read_reference_table(path)
                self.assertEqual(data.shape[0],20)
                np.testing.assert_allclose(data[:,0],sim.snapshot()["depth_a"])
        self.assertIn("STATUS = NOT AVAILABLE",output["VACANCY.txt"])
        self.assertIn("STATUS = NOT AVAILABLE",output["NOVAC.txt"])
        self.assertIn("BY_IONS",output["IONIZ.txt"])
        self.assertIn("BY_RECOILS",output["IONIZ.txt"])

    def test_bundle_selection_and_unique_paths(self):
        state=populated().snapshot()
        with tempfile.TemporaryDirectory() as folder:
            a=export_bundle(state,folder,selected={"RANGE.txt"})
            b=export_bundle(state,folder,selected={"IONIZ.txt"})
            self.assertNotEqual(a,b)
            self.assertTrue((a/"TDATA.txt").is_file())
            self.assertFalse((a/"IONIZ.txt").exists())
            self.assertTrue((b/"IONIZ.txt").is_file())
            self.assertTrue((a/"project.json").is_file())

    def test_diagnostic_exports_rejected(self):
        sim=populated();sim.records[0][0,16]=1
        with self.assertRaises(ValueError):text_outputs(sim.snapshot())

    def test_legacy_split_not_invented(self):
        sim=populated();sim.detail_complete=False
        self.assertEqual(sim.snapshot()["detail_profiles"],{})
        self.assertIn("TOTAL_NO_SPLIT",text_outputs(sim.snapshot())["IONIZ.txt"])

    def test_detail_checkpoint_roundtrip_and_legacy_missing_data(self):
        sim=populated()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"checkpoint.npz";sim.save_checkpoint(path)
            restored=Simulation.load_checkpoint(path)
            np.testing.assert_array_equal(restored.detail_hist,sim.detail_hist)
            self.assertTrue(restored.detail_complete)
            with np.load(path,allow_pickle=False) as data:
                old={k:data[k] for k in data.files if k not in ("detail_hist","detail_complete")}
            np.savez(path,**old)
            oldsim=Simulation.load_checkpoint(path)
            self.assertFalse(oldsim.detail_complete)
            self.assertEqual(oldsim.snapshot()["detail_profiles"],{})

    def test_bad_detail_checkpoint_rejected(self):
        sim=populated()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"checkpoint.npz";sim.save_checkpoint(path)
            with np.load(path,allow_pickle=False) as data:values={k:data[k] for k in data.files}
            values["detail_hist"]=np.zeros((2,20));np.savez(path,**values)
            with self.assertRaisesRegex(ValueError,"detailed"):Simulation.load_checkpoint(path)

    def test_reference_parser_and_column_names(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"RANGE.txt"
            path.write_text("An untrusted header is just text.\n DEPTH He Si Al\n1.234.E+02 2.E+03 3.E+03 4.E+03\n2.345E+02 1.0 2.0 3.0\n",encoding="utf-8")
            # Standard FORTRAN forms with a trailing decimal before exponent.
            path.write_text(path.read_text().replace("1.234.E","1234.E"),encoding="utf-8")
            data=read_reference_table(path)
            self.assertEqual(data.shape,(2,4))
            plot=reference_plots(folder)["range"]
            self.assertEqual([s[0] for s in plot.series],["He","Si","Al"])

    def test_plot_language_and_spectrum_axes(self):
        state=populated().snapshot()
        self.assertNotEqual(plot_from_snapshot(state,"range","zh").title,plot_from_snapshot(state,"range","en").title)
        self.assertEqual(plot_from_snapshot(state,"sputtered").xmax,1000)
        self.assertEqual(plot_from_snapshot(state,"transmitted").xmax,5000)


@unittest.skipUnless(os.environ.get("GSRIM_TEST_GPU")=="1","GPU tests not requested")
class DetailedGpuTests(unittest.TestCase):
    def test_real_gpu_tallies_reconcile_with_aggregate_and_ledger(self):
        p=copy.deepcopy(DEFAULT);p["run"].update(ions=16,batch_size=8)
        with tempfile.TemporaryDirectory() as folder:
            sim=Simulation(p,checkpoint_path=Path(folder)/"autosave.npz")
            sim.start();sim.thread.join(60)
            self.assertFalse(sim.thread.is_alive());self.assertEqual(sim.status,"completed",sim.error)
            for total,a,b in [(1,0,1),(2,2,3),(5,4,5)]:
                np.testing.assert_allclose(sim.hist[total],sim.detail_hist[a]+sim.detail_hist[b],atol=1e-8)
            nt=(sim.detail_hist.shape[0]-len(DETAIL_CHANNELS))//2
            np.testing.assert_allclose(sim.hist[4],sim.detail_hist[7:7+nt].sum(axis=0),atol=1e-8)
            np.testing.assert_allclose(sim.hist[3],sim.detail_hist[7+nt:].sum(axis=0),atol=1e-8)
            r=np.concatenate(sim.records)
            for channel,record in [(0,4),(1,6),(2,5),(3,7)]:
                self.assertAlmostEqual(sim.detail_hist[channel].sum(),r[:,record].sum(),places=7)
            restored=Simulation.load_checkpoint(Path(folder)/"autosave.npz")
            np.testing.assert_array_equal(restored.detail_hist,sim.detail_hist)
