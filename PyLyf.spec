# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\code_\\PyLyf\\PyLyf.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\code_\\PyLyf\\included_data\\CONFIG', '.'), ('C:\\code_\\PyLyf\\included_data\\DATES.csv', '.'), ('C:\\code_\\PyLyf\\included_data\\STYLE.css', '.'), ('C:\\code_\\PyLyf\\included_data\\example_1.jpg', '.'), ('C:\\code_\\PyLyf\\included_data\\example_2.jpg', '.'), ('C:\\code_\\PyLyf\\included_data\\example_3.jpg', '.'), ('C:\\code_\\PyLyf\\included_data\\example_4.jpg', '.')],
    hiddenimports=[],
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
    name='PyLyf',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name='PyLyf',
)
