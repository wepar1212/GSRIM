import os
import unittest
import numpy as np


class IaeaStoppingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from gsrim.iaea_stopping import find_iaea_csv
        cls.csv = find_iaea_csv()

    def test_csv_present(self):
        if self.csv is None:
            self.skipTest("IAEA StoppingPower.csv not downloaded")
        self.assertTrue(self.csv.is_file())
        self.assertGreater(self.csv.stat().st_size, 1_000_000)

    def test_h_si_series_physical(self):
        if self.csv is None:
            self.skipTest("no IAEA CSV")
        from gsrim.se_tables import iaea_index
        idx = iaea_index(force_reload=True)
        ser = idx.get(("H", "Si"))
        self.assertIsNotNone(ser)
        self.assertGreater(ser.n_points, 10)
        # High-energy Se should be tens of eV/A, not 1e-6 or 1e6
        se = ser.evaluate(min(ser.energy_ev[-1] * 0.5, 1e7))
        self.assertGreater(se, 0.5)
        self.assertLess(se, 500)

    def test_se_for_pair_bv_or_iaea(self):
        if self.csv is None:
            self.skipTest("no IAEA CSV")
        from gsrim.se_tables import se_for_pair, default_energy_grid
        e = default_energy_grid(10, 1e6, 64)
        se, src = se_for_pair(
            "He", 2, 4.0026,
            [("Si", 14, 28.085, 1.0)],
            0.05, 2.329, e, model="iaea",
        )
        self.assertEqual(se.shape, e.shape)
        self.assertTrue(np.all(np.isfinite(se)))
        self.assertTrue(np.all(se > 0))
        self.assertTrue(src.startswith("IAEA") or src.startswith("NIST") or src in ("BV", "LS"))

    def test_energy_conservation_with_se_table(self):
        if self.csv is None or os.environ.get("GSRIM_TEST_GPU") != "1":
            self.skipTest("GPU or CSV missing")
        import copy
        from gsrim.project import DEFAULT
        from gsrim.simulation import Simulation
        p = copy.deepcopy(DEFAULT)
        p["run"]["ions"] = 16
        p["run"]["batch_size"] = 16
        p["run"]["mode"] = "ions"
        p["physics"]["stopping"] = "iaea"
        p["ion"] = {"symbol": "He", "z": 2, "mass_u": 4.0026, "energy_kev": 30, "angle_deg": 0}
        s = Simulation(p)
        s.start(); s.thread.join(60)
        self.assertEqual(s.status, "completed", s.error)
        self.assertLess(s.snapshot()["stats"]["max_energy_error_ev"], 1e-4)


if __name__ == "__main__":
    unittest.main()
