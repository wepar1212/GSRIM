# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from pathlib import Path

root = Path(SPECPATH)
datas = [(str(root / 'gsrim' / 'kernels'), 'gsrim/kernels')]
binaries = []
hiddenimports = ['gsrim', 'gsrim.server', 'gsrim.desktop', 'gsrim.simulation', 'gsrim.project', 'gsrim.materials', 'gsrim.scattering', 'gsrim.compounds', 'gsrim.electronic_stopping', 'gsrim.iaea_stopping', 'gsrim.nist_stopping', 'gsrim.se_tables', 'gsrim.scatter_table', 'gsrim.gpu_environment', 'cupy']
tmp_ret = collect_all('cupy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('cupy_backends')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
# Only the CUDA runtime/compiler and their headers, never a copied venv.
import importlib.util
for component in ('nvidia.cuda_runtime', 'nvidia.cuda_nvrtc'):
    location = Path(next(iter(importlib.util.find_spec(component).submodule_search_locations)))
    target = component.replace('.', '/')
    for folder in ('bin', 'include'):
        if (location / folder).is_dir():
            datas.append((str(location / folder), target + '/' + folder))
hiddenimports += ['gsrim.portable', 'gsrim.output', 'gsrim.native_plot',
                  'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets']
from PySide6.QtCore import QLibraryInfo
translations = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
for translation in translations.glob('qtbase_zh_CN.qm'):
    datas.append((str(translation), 'PySide6/translations'))
hiddenimports += ['fastrlock', 'fastrlock.rlock']


a = Analysis(
    [str(root / 'build' / 'desktop_entry.py')],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'IPython', 'pytest', 'tkinter', 'torch', 'PyQt5', 'PyQt6', 'PySide2',
              'webview', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQuick', 'PySide6.QtQml'],
    noarchive=False,
    optimize=0,
)
# Qt 6.12 uses Windows' system ICU with unversioned exports. Do not bundle
# an incompatible ICU from unrelated programs on the build machine's PATH.
# Windows 10/11 already supply ICU, API-set forwarders and the universal CRT.
a.binaries = [entry for entry in a.binaries
              if not (Path(entry[0]).name.lower() in ('icuuc.dll', 'ucrtbase.dll')
                      or Path(entry[0]).name.lower().startswith(('api-ms-', 'icudt')))]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GSRIM',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GSRIM',
)
