"""Optional GPU tests; enable explicitly with GSRIM_TEST_GPU=1."""
import os
import unittest
import numpy as np
from gsrim.scattering import scatter


@unittest.skipUnless(os.environ.get("GSRIM_TEST_GPU") == "1", "GPU tests not requested")
class GpuTests(unittest.TestCase):
    def test_cpu_gpu_agreement(self):
        for z1,z2,m1,m2 in [(1,14,1,28), (18,74,40,184), (2,6,4,12)]:
            energy = np.geomspace(100, 1e6, 97)
            impact = np.geomspace(.001, 1, 97)
            for screened in (True, False):
                args = dict(z1=z1,z2=z2,m1=m1,m2=m2,screened=screened)
                cpu = scatter(energy,impact,**args)
                gpu = scatter(energy,impact,engine="gpu",**args)
                for expected,actual in zip(cpu,gpu):
                    np.testing.assert_allclose(actual.get(),expected,atol=2e-6,rtol=1e-6)

    def test_zero_impact_and_broadcast(self):
        args=dict(z1=14,z2=14,m1=28,m2=28)
        angle,recoil,root = scatter(np.array([[100],[1000]]), [0,.1],engine="gpu",**args)
        self.assertEqual(angle.shape,(2,2))
        np.testing.assert_allclose(recoil.get()[:,0],[100,1000])

    def test_empty_batch(self):
        result=scatter([],[],z1=1,z2=1,m1=1,m2=1,engine="gpu")
        self.assertEqual(result[0].size,0)
