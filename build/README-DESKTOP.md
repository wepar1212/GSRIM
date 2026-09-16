# Local desktop packaging (experimental)

First install requirements-desktop.txt into the project .venv, then install
PyInstaller there. From the repository root run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build\make_deliverable.ps1
```

The script creates a unique dist/source-build-*/GSRIM directory and preserves
existing portable packages. The spec resolves paths relative to the checkout.
No third-party stopping datasets or copied virtual environment are bundled.

This source release does not certify frozen-executable portability. Verify
CUDA DLL loading, WebView2, GPU execution and output paths on a clean machine.
Review all dependency licenses (especially NVIDIA components) and include
required notices before distributing binaries. No binary release is published
with the initial source repository.
