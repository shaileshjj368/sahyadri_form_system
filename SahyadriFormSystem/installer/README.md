# Windows packaging

- `build_windows.ps1` (or double-click `..\build_windows.bat`) builds
  `dist\SahyadriFormSystem\` with PyInstaller and zips it to
  `dist\SahyadriFormSystem-Windows.zip` for the customer.
- `-WithOfflineSpeech` also bundles the optional offline speech model
  (`prepare_offline_stt.ps1` downloads it). Not needed for the default online speech.

A proper installer (Start-menu shortcut, uninstaller) can be added later by wrapping
`dist\SahyadriFormSystem\` with Inno Setup; the app itself needs no changes for that.
