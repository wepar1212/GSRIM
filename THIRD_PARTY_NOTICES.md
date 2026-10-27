# Third-party components and scientific references

The MIT license at the repository root covers GSRIM's own code and documents,
not separately obtained libraries, datasets, SRIM, or NVIDIA components.

Dependencies are installed separately. NumPy, SciPy, CuPy, PySide6/Shiboken6 and their
dependencies retain their upstream licenses. NVIDIA CUDA Runtime and NVRTC
are proprietary components governed by NVIDIA's terms, not this MIT license.
This source release does not distribute their binaries, Python environments,
or the locally built portable executable.

The native desktop uses Qt for Python / PySide6 Essentials. Qt libraries are
dynamically loaded and unmodified. They retain their LGPLv3/GPL/commercial
terms; the MIT license does not replace those terms. Compatible library
replacement and debugging library modifications are not restricted by GSRIM.
Upstream sources: https://code.qt.io/cgit/pyside/pyside-setup.git/ and
https://code.qt.io/cgit/qt/ . Local packages include upstream license files and
their build versions under licenses/. No Qt WebEngine is used.

SRIM/TRIM binaries and stopping tables are not included or invoked. This is
an independent research implementation, not an official SRIM distribution.

The editable elemental setup suggestions include factual atomic properties and
positive sublimation-energy values transcribed from an SRIM-RE ATOMDATA
export, plus explicitly identified material-input examples. Elemental
displacement suggestions otherwise use Table 4 of Konobeyev et al. (2017),
https://doi.org/10.1016/j.nucet.2017.08.007 . These suggestions are not a recovered
complete SRIM default database. Sources, assumptions and missing values are
recorded in docs/ELEMENT_DEFAULTS.md and gsrim/element_defaults.py. The source
article and original SRIM files retain their own terms and are not bundled.

Scientific references include the ZBL screened potential, Lindhard-Scharff
electronic stopping and Biersack-Varelas/Bethe models. The BV expression was
cross-checked against the RustBCA project:
https://github.com/lcpp-org/RustBCA (see src/material.rs).
This attribution is not a claim of numerical equivalence or endorsement.

External IAEA and NIST stopping datasets are not part of this source release.
See data/README.md for sources, placement and reproducibility requirements.
Before distributing a binary bundle, review the licenses and redistribution
requirements of every included dependency and dataset separately.
