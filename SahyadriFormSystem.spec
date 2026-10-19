# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[('C:/Users/shail/AppData/Local/Programs/Python/Python314/Lib/site-packages/speech_recognition/flac-win32.exe', 'speech_recognition')],
    datas=[('templates', 'templates'), ('fonts', 'fonts'), ('C:/Users/shail/AppData/Local/Programs/Python/Python314/Lib/site-packages/speech_recognition/version.txt', 'speech_recognition')],
    hiddenimports=['speech_recognition.recognizers.google'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['faster_whisper', 'ctranslate2', 'av', 'onnxruntime'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SahyadriFormSystem',
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
    name='SahyadriFormSystem',
)
