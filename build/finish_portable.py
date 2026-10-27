"""Add documentation/notices to a newly built local distribution (no downloads)."""
import argparse
from importlib import metadata
from pathlib import Path
import shutil
import sys

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
args = parser.parse_args()
package = args.package.resolve()
if root / "dist" not in package.parents or not (package / "GSRIM.exe").is_file():
    raise SystemExit("Expected an existing package under the project's dist directory")
for source, name in [(root / "LICENSE", "LICENSE"),
                     (root / "build/PORTABLE-README.txt", "README.txt"),
                     (root / "data/README.md", "DATA-README.md"),
                     (root / "docs/ELEMENT_DEFAULTS.md", "ELEMENT-DEFAULTS.md"),
                     (root / "docs/element-defaults.csv", "element-defaults.csv"),
                     (root / "build/GPU-Self-Test.cmd", "GPU-Self-Test.cmd")]:
    shutil.copy2(source, package / name)
notices = package / "licenses"
notices.mkdir(exist_ok=True)
qt_notices=notices/"Qt"
qt_notices.mkdir(exist_ok=True)
for name in ("qt-LGPL-3.0.txt","qt-GPL-3.0.txt"):
    shutil.copy2(root/"build"/name,qt_notices/name.removeprefix("qt-"))
(qt_notices/"SOURCES.txt").write_text(
    "Unmodified Qt/PySide6/Shiboken6 shared libraries. The selected LGPLv3 "
    "option is accompanied by LGPL-3.0.txt and its GPL-3.0.txt terms. "
    "See COMPONENTS.txt for exact build versions. Qt/PySide source and "
    "build instructions: https://code.qt.io/cgit/pyside/pyside-setup.git/ "
    "and https://code.qt.io/cgit/qt/ (matching version tags). Compatible "
    "library replacement and debugging modifications are not restricted "
    "by GSRIM. No Qt WebEngine is bundled.\n",encoding="utf-8")
names = ["numpy", "scipy", "cupy-cuda12x", "fastrlock", "PySide6-Essentials", "shiboken6",
         "pythonnet", "clr-loader", "cffi", "pycparser", "typing_extensions",
         "proxy-tools", "bottle", "pywin32", "pywin32-ctypes", "setuptools",
         "packaging", "importlib-metadata", "zipp", "charset-normalizer",
         "requests", "urllib3", "idna", "certifi", "psutil", "tornado",
         "PyYAML", "cryptography", "pyreadline3", "six", "pyinstaller",
         "nvidia-cuda-runtime-cu12", "nvidia-cuda-nvrtc-cu12"]
rows = []
for name in names:
    try:
        dist = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        continue
    rows.append(f"{dist.metadata['Name']}=={dist.version}")
    for item in dist.files or []:
        if any(word in str(item).lower() for word in ("license", "copying", "notice", "copyright")):
            source = dist.locate_file(item)
            if source.is_file():
                relative = Path(*[part for part in item.parts if part not in ("..", ".")])
                target = notices / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.is_file():
    shutil.copy2(python_license, notices / "PYTHON-LICENSE.txt")
(notices / "COMPONENTS.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")
(package / "THIRD-PARTY.txt").write_text(
    "GSRIM's own code is MIT licensed. Bundled third-party components retain "
    "their original licenses in licenses/. NVIDIA CUDA Runtime/NVRTC are "
    "proprietary, supplied solely for use with this application under the "
    "included NVIDIA terms. No grant in the MIT license overrides those terms. "
    "Do not separate or redistribute NVIDIA components contrary to their terms. "
    "No NVIDIA display driver or external stopping datasets are bundled. "
    "Qt for Python (PySide6/Shiboken6) is provided as dynamically loaded, "
    "unmodified libraries under its included LGPLv3/GPL/commercial terms; "
    "consult licenses/PySide6-Essentials and licenses/shiboken6 for the terms "
    "and upstream source information. GSRIM does not restrict debugging of "
    "modifications to these libraries or replacement of compatible libraries. "
    "Qt source: https://code.qt.io/cgit/pyside/pyside-setup.git/ and "
    "https://code.qt.io/cgit/qt/ . "
    "The component list records build-environment versions and may include "
    "notices for optional dependencies not used at runtime.\n",
    encoding="utf-8")
print("Documentation and notices added:", package)
