"""Process-local DLL setup for the project-local NVIDIA wheel installation."""
import os
from pathlib import Path
import sys

_handles = []


def configure():
    if os.name != "nt" or _handles:
        return
    root = Path(sys.prefix) / "Lib/site-packages/nvidia"
    runtime = root / "cuda_runtime"
    if runtime.is_dir():
        os.environ.setdefault("CUDA_PATH", str(runtime))
    for component in ("cuda_runtime", "cuda_nvrtc"):
        directory = root / component / "bin"
        if directory.is_dir():
            _handles.append(os.add_dll_directory(str(directory)))
            # NVRTC loads its builtins internally using the process search path.
            os.environ["PATH"] = str(directory) + os.pathsep + os.environ.get("PATH", "")
