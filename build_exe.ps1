# Builds a standalone, no-console-window .exe with PyInstaller.
# The Whisper model is NOT bundled - it downloads on first run into
# %LOCALAPPDATA%\wisper-clone\models the first time the app records something.
#   powershell -ExecutionPolicy Bypass -File build_exe.ps1

$ErrorActionPreference = "Stop"

$venvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found. Run setup.ps1 first."
}

& $venvPython -m pip install --upgrade pyinstaller

& $venvPython -m PyInstaller `
    --noconsole `
    --onefile `
    --name "LocalDictation" `
    --paths "src" `
    "src\main.py"

Write-Host ""
Write-Host "Build complete: dist\LocalDictation.exe"
Write-Host "Copy config.example.json next to the exe as config.json to customize settings before first run."
Write-Host "To run at login, create a shortcut to the exe in: shell:startup"
