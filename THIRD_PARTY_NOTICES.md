# Third-party components and scientific references

The MIT license at the repository root covers GSRIM's own code and documents,
not separately obtained libraries, datasets, SRIM, or NVIDIA components.

Dependencies are installed separately. NumPy, SciPy, CuPy, pywebview and their
dependencies retain their upstream licenses. NVIDIA CUDA Runtime and NVRTC
are proprietary components governed by NVIDIA's terms, not this MIT license.
This source release does not distribute their binaries, Python environments,
or the locally built portable executable.

SRIM/TRIM binaries and stopping tables are not included or invoked. This is
an independent research implementation, not an official SRIM distribution.

Scientific references include the ZBL screened potential, Lindhard-Scharff
electronic stopping and Biersack-Varelas/Bethe models. The BV expression was
cross-checked against the RustBCA project:
https://github.com/lcpp-org/RustBCA (see src/material.rs).
This attribution is not a claim of numerical equivalence or endorsement.

External IAEA and NIST stopping datasets are not part of this source release.
See data/README.md for sources, placement and reproducibility requirements.
Before distributing a binary bundle, review the licenses and redistribution
requirements of every included dependency and dataset separately.
