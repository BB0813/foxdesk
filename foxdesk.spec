# -*- mode: python ; coding: utf-8 -*-
# FoxDesk PyInstaller Spec

from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH)

datas = [
    ('static', 'static'),
    ('backend', 'backend'),
]
binaries = []
hiddenimports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'pydantic',
    'pydantic.deprecated.decorator',
    'starlette',
    'starlette.routing',
    'starlette.responses',
    'starlette.staticfiles',
    'starlette.middleware',
    'starlette.middleware.cors',
    'webview',
    'camoufox',
    'camoufox.__main__',
    'camoufox.sync_api',
    'camoufox.async_api',
    'camoufox.server',
    'camoufox.utils',
    'camoufox.fingerprints',
    'camoufox.pkgman',
    'camoufox.addons',
    'camoufox.locale',
    'camoufox.ip',
    'camoufox.webgl',
    'camoufox.exceptions',
    'camoufox.warnings',
    'camoufox.__version__',
    'browserforge',
    'browserforge.fingerprints',
    'browserforge.headers',
    'browserforge.download',
    'multipart',
    'anyio',
    'anyio._backends',
    'anyio._backends._asyncio',
    'orjson',
    'click',
    'yaml',
    'platformdirs',
    'requests',
    'tqdm',
    'playwright',
    'playwright.sync_api',
    'playwright.async_api',
    'language_tags',
    'screeninfo',
    'backend',
    'backend.app',
    'backend.camoufox_worker',
    'backend.process_utils',
    'backend.proxy_pool',
    'backend.templates_data',
    'backend.setup_manager',
    'backend.update_manager',
    'pystray',
    'pystray._base',
    'pystray._win32',
    'PIL',
    'PIL.Image',
]

# Ensure camoufox + fingerprint data files and submodules ship with the installer.
for pkg in ('camoufox', 'browserforge', 'language_tags'):
    try:
        pkg_datas, pkg_binaries, pkg_hidden = collect_all(pkg)
        datas += pkg_datas
        binaries += pkg_binaries
        hiddenimports += pkg_hidden
    except Exception as exc:
        print(f'[foxdesk.spec] collect_all({pkg}) skipped: {exc}')

try:
    hiddenimports += collect_submodules('camoufox')
except Exception:
    pass
try:
    hiddenimports += collect_submodules('browserforge')
except Exception:
    pass

# de-dup while preserving order
_seen = set()
_unique_hidden = []
for name in hiddenimports:
    if name and name not in _seen:
        _seen.add(name)
        _unique_hidden.append(name)
hiddenimports = _unique_hidden

a = Analysis(
    ['desktop.py'],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FoxDesk',
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
    icon=str(ROOT / 'static' / 'logo.ico') if (ROOT / 'static' / 'logo.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FoxDesk',
)
