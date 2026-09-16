import unittest
from gsrim.validation import VALIDATION_TARGETS, project_for_target, RangeTarget


class ValidationSchemaTests(unittest.TestCase):
    def test_targets_project_validate(self):
        for t in VALIDATION_TARGETS:
            p = project_for_target(t, ions=16)
            self.assertGreaterEqual(p["layers"][0]["thickness_a"], t.projected_range_nm * 10)
            self.assertEqual(p["ion"]["z"], t.ion_z)

    def test_ratio_math(self):
        t = VALIDATION_TARGETS[0]
        self.assertAlmostEqual(t.ratio(200.0), 200.0 / t.projected_range_nm)
        self.assertIsNone(t.ratio(None))
