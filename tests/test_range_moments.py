import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np

from gsrim.output import plot_from_snapshot, reference_plots, text_outputs
from gsrim.project import DEFAULT
from gsrim.simulation import NREC, Simulation


def endpoints(depths, statuses=None, bins=20):
    project=copy.deepcopy(DEFAULT)
    project['run'].update(ions=max(1,len(depths)),bins=bins)
    sim=Simulation(project)
    records=np.zeros((len(depths),NREC))
    records[:,3]=depths
    if statuses is not None:records[:,0]=statuses
    sim.records=[records];sim.completed=len(depths);sim.status='completed'
    return sim


class RangeMomentTests(unittest.TestCase):
    def test_population_moments_exclude_escaping_ions_and_ignore_bins(self):
        for bins in (20,160):
            sim=endpoints([100,100,100,300,-9999,9999],[0,0,0,0,1,2],bins)
            stats=sim.snapshot()['stats']
            self.assertEqual(stats['mean_range_a'],150)
            self.assertAlmostEqual(stats['range_straggle_a'],np.sqrt(7500))
            self.assertAlmostEqual(stats['range_skewness'],2/np.sqrt(3))
            self.assertAlmostEqual(stats['range_kurtosis'],7/3)
            self.assertEqual(sim.hist.sum(),0)  # Raw endpoints, no histogram inference.

    def test_pearson_kurtosis_is_not_excess(self):
        stats=endpoints([100,200,200,200,200,300]).snapshot()['stats']
        self.assertAlmostEqual(stats['range_skewness'],0)
        self.assertAlmostEqual(stats['range_kurtosis'],3)

    def test_empty_or_constant_endpoints_have_no_shape_moments(self):
        for sim in (endpoints([100],[1]),endpoints([100]),endpoints([100,100])):
            stats=sim.snapshot()['stats']
            self.assertIsNone(stats['range_skewness'])
            self.assertIsNone(stats['range_kurtosis'])
            chart=plot_from_snapshot(sim.snapshot(),'range','en')
            self.assertEqual(chart.statistics[2:], [('Skewness','N/A'),('Kurtosis','N/A')])

    def test_diagnostic_and_older_json_do_not_invent_shape_moments(self):
        sim=endpoints([100,300]);sim.records[0][0,16]=1
        state=sim.snapshot()
        self.assertTrue(state['diagnostic_only'])
        self.assertTrue(all(value=='N/A' for _,value in plot_from_snapshot(state).statistics))
        state=endpoints([100,300]).snapshot()
        state['stats'].pop('range_skewness');state['stats'].pop('range_kurtosis')
        self.assertEqual(plot_from_snapshot(state,'range','en').statistics[2:],
                         [('Skewness','N/A'),('Kurtosis','N/A')])

    def test_checkpoint_recomputes_and_text_roundtrip_preserves_moments(self):
        sim=endpoints([100,100,100,300])
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            sim.save_checkpoint(folder/'checkpoint.npz')
            restored=Simulation.load_checkpoint(folder/'checkpoint.npz')
            self.assertAlmostEqual(restored.snapshot()['stats']['range_kurtosis'],7/3)
            state=sim.snapshot()
            output=text_outputs(state)
            self.assertIn('Range skewness',output['TDATA.txt'])
            (folder/'RANGE.txt').write_text(output['RANGE.txt'],encoding='utf8')
            reference=reference_plots(folder,'en')['range']
            self.assertEqual(reference.statistics,plot_from_snapshot(state,'range','en').statistics)

    def test_srim_reference_moments_are_read_from_the_header(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'RANGE.txt'
            p.write_text('Ion Average Range = 279.2E+01 A Straggling = 682.6E+00 A\n'
                         'Range Skewne- = -000.8062 &= [formula]\nRange Kurtosis = 004.0287\n'
                         'DEPTH H O\n10 1 2\n20 3 4\n',encoding='utf8')
            chart=reference_plots(folder,'en')['range']
            self.assertEqual(chart.statistics,[('Ion Range','2792 Å'),('Straggle','682.6 Å'),
                                               ('Skewness','-0.8062'),('Kurtosis','4.0287')])


if __name__=='__main__':
    unittest.main()
