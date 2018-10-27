# -*- mode: python -*-

block_cipher = None


a = Analysis(['/Users/ju/gtk/inst/bin/com.github.geigi.cozy'],
             pathex=['/Users/ju/cozy'],
             binaries=[],
             datas=[ ('/Users/ju/gtk/inst/share/cozy/*.gresource', '.'), 
                     ('/Users/ju/gtk/inst/share/misc', 'share/misc'),
                     ('/Users/ju/gtk/inst/lib/libmagic.dylib', '.') ],
             hiddenimports=[ 'cairo' ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='Cozy',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='Cozy')
app = BUNDLE(coll,
             name='Cozy.app',
             icon='data/icons/com.github.geigi.cozy.icns',
             bundle_identifier=None,
info_plist={
            'NSPrincipleClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            },
         )
