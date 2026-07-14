# -*- mode: python ; coding: utf-8 -*-
# FoxDesk PyInstaller Spec

from pathlib import Path

ROOT = Path(SPECPATH)

a = Analysis(
    ['desktop.py'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        ('static', 'static'),
        ('backend', 'backend'),
    ],
    hiddenimports=[
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
        'camoufox.sync_api',
        'camoufox.async_api',
        'camoufox.server',
        'camoufox.utils',
        'camoufox.fingerprints',
        'browserforge',
        'browserforge.fingerprints',
        'multipart',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        'backend',
        'backend.app',
        'backend.camoufox_worker',
    ],
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
