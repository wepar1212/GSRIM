"""Run regression tests without touching application autosaves."""
import argparse
import os
from pathlib import Path
import tempfile
import unittest

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--gpu",action="store_true")
    args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="gsrim-regression-") as folder:
        os.environ["GSRIM_RESULTS_DIR"]=folder
        os.environ["GSRIM_TEST_GPU"]="1" if args.gpu else "0"
        suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent/"tests"))
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        raise SystemExit(not result.wasSuccessful())
