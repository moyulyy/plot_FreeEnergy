# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置 —— Energy Profile Studio 单文件免安装 exe

用法（在 chem_env 中）:
    python -m PyInstaller --noconfirm --clean EnergyProfileStudio.spec

说明:
    conda 环境的 Python 标准库扩展 (pyexpat / zlib / _lzma / _ctypes / _ssl ...)
    依赖 %CONDA%\\Library\\bin 下的 DLL，PyInstaller 默认不会收集，
    因此这里显式把它们加入，避免 "DLL load failed while importing pyexpat"。
"""
import os
import sys

CONDA_PREFIX = sys.base_prefix
LIBBIN = os.path.join(CONDA_PREFIX, "Library", "bin")

# Windows API Set 由系统提供，不能打包；tcl/tk 不使用
SKIP_PREFIX = ("api-ms-win-",)
SKIP_NAME = {"ucrtbase.dll", "tcl86t.dll", "tk86t.dll",
             "python3.dll", "python311.dll", "python3.dll"}

binaries = []
if os.path.isdir(LIBBIN):
    for name in sorted(os.listdir(LIBBIN)):
        low = name.lower()
        if not low.endswith(".dll"):
            continue
        if low.startswith(SKIP_PREFIX) or low in SKIP_NAME:
            continue
        binaries.append((os.path.join(LIBBIN, name), "."))

a = Analysis(
    ["Plot_EnergyProfile-Studio.py"],
    pathex=["."],
    binaries=binaries,
    datas=[],
    hiddenimports=["plot_core"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "_tkinter", "PyQt5", "PyQt6",
        "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick", "PySide6.QtQml", "PySide6.QtQuick",
        "PySide6.QtQuick3D", "PySide6.QtMultimedia", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.Qt3DCore", "PySide6.Qt3DRender",
        "pandas", "openpyxl", "scipy", "IPython", "notebook",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="EnergyProfileStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="app.ico",
)
