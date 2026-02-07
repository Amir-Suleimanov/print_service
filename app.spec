# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['tray.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'api',
        'api.routes',
        'api.validators',
        'services',
        'services.converter',
        'services.printer',
        'services.queue',
        'utils',
        'utils.logger',
        'flask',
        'waitress',
        'pystray._win32',
    ],
    excludes=[],
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='PrintService',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
    uac_admin=False,
)