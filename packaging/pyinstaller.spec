# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
import sys


project_root = Path.cwd().resolve()
src_root = project_root / "src"
gui_entry = src_root / "thesis_format_fixer" / "gui.py"
rules_dir = project_root / "rules"

datas = [(str(rules_dir), "rules")]

a = Analysis(
    [str(gui_entry)],
    pathex=[str(src_root)],
    binaries=[],
    datas=datas,
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
    [],
    exclude_binaries=True,
    name="ThesisFormatFixer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == "darwin":
    app = BUNDLE(
        exe,
        a.binaries,
        a.datas,
        name="ThesisFormatFixer.app",
        icon=None,
        bundle_identifier=None,
    )
else:
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="ThesisFormatFixer",
    )
