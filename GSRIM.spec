# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from pathlib import Path

root = Path(SPECPATH)
datas = [(str(root / 'web'), 'web'), (str(root / 'gsrim' / 'kernels'), 'gsrim/kernels')]
binaries = []
hiddenimports = ['gsrim', 'gsrim.server', 'gsrim.desktop', 'gsrim.simulation', 'gsrim.project', 'gsrim.materials', 'gsrim.scattering', 'gsrim.compounds', 'gsrim.electronic_stopping', 'gsrim.iaea_stopping', 'gsrim.nist_stopping', 'gsrim.se_tables', 'gsrim.scatter_table', 'gsrim.gpu_environment', 'cupy']
tmp_ret = collect_all('cupy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('nvidia')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    [str(root / 'gsrim' / 'desktop.py')],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
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
