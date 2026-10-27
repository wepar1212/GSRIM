import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from gsrim import gpu_environment
from gsrim.portable import configure_storage
from gsrim.scatter_table import _cache_path


class PortableTests(unittest.TestCase):
    def test_frozen_cuda_paths_use_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for part in ('cuda_runtime', 'cuda_nvrtc'):
                (base / 'nvidia' / part / 'bin').mkdir(parents=True)
            with patch.object(gpu_environment, '_handles', []), \
                 patch('sys.frozen', True, create=True), \
                 patch('sys._MEIPASS', folder, create=True), \
                 patch.dict(os.environ, {'CUDA_PATH': 'old-machine-path'}), \
                 patch('os.add_dll_directory', create=True) as add:
                gpu_environment.configure()
                self.assertEqual(os.environ['CUDA_PATH'], str(base / 'nvidia/cuda_runtime'))
                self.assertEqual(add.call_count, 2)

    def test_storage_follows_executable(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=True):
            with patch('sys.executable', str(Path(folder) / 'GSRIM.exe')):
                result = configure_storage()
            # Windows runners may return an 8.3 alias from tempfile, while
            # configure_storage deliberately resolves the executable's path.
            self.assertEqual(result, Path(folder).resolve() / 'results')
            self.assertEqual(Path(os.environ['GSRIM_RESULTS_DIR']), result / 'revision-4')
            self.assertEqual(_cache_path(4, 4, (1, 2), (1, 2), 8).parent, result / 'tables')
