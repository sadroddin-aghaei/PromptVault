# -*- mode: python ; coding: utf-8 -*-
# Local build:   pyinstaller PromptVault.spec
# Windows 1-file: set PV_ONEFILE=1 && pyinstaller PromptVault.spec
# macOS universal2: PV_ARCH=universal2 pyinstaller PromptVault.spec   (needs a universal2 Python)
import os
import sys
from PyInstaller.utils.hooks import collect_data_files

sys.path.insert(0, os.path.abspath("."))
from app import APP_VERSION, COPYRIGHT  # noqa: E402

ONEFILE = os.environ.get("PV_ONEFILE", "0") == "1" and sys.platform != "darwin"
TARGET_ARCH = os.environ.get("PV_ARCH") or None          # macOS only: arm64 | x86_64 | universal2
IS_MAC = sys.platform == "darwin"

datas = [("assets", "assets")] + collect_data_files("qtawesome")
ICON = "assets/icons/promptvault.icns" if IS_MAC else "assets/icons/promptvault.ico"
if not os.path.exists(ICON):
    ICON = None

a = Analysis(
    ["main.py"], pathex=["."], datas=datas,
    hiddenimports=["sqlalchemy.dialects.sqlite"],
    excludes=["tkinter", "greenlet", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
              "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtMultimedia", "PySide6.QtCharts",
              "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtSql", "PySide6.QtTest"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="PromptVault", console=False, icon=ICON,
              upx=False, runtime_tmpdir=None)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="PromptVault", console=False, icon=ICON,
              upx=False, target_arch=TARGET_ARCH)
    coll = COLLECT(exe, a.binaries, a.datas, name="PromptVault", upx=False)
    if IS_MAC:
        app = BUNDLE(
            coll, name="Prompt Vault.app", icon=ICON, bundle_identifier="com.sadroddinaghaei.promptvault",
            version=APP_VERSION,
            info_plist={
                "CFBundleName": "Prompt Vault", "CFBundleDisplayName": "Prompt Vault",
                "CFBundleShortVersionString": APP_VERSION, "CFBundleVersion": APP_VERSION,
                "NSHumanReadableCopyright": COPYRIGHT, "NSHighResolutionCapable": True,
                "LSApplicationCategoryType": "public.app-category.productivity",
                "CFBundleDevelopmentRegion": "en", "CFBundleLocalizations": ["en", "fa"],
            },
        )
