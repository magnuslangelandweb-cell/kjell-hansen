# Builds a standalone, no-console-window .exe with PyInstaller.
# The Whisper model is NOT bundled - it downloads into a "models" folder next
# to the .exe the first time the app transcribes something. Logs go to a
# "logs" folder next to the .exe too (see src/paths.py).
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

Copy-Item "config.example.json" "dist\config.example.json" -Force

Write-Host ""
Write-Host "Build complete: dist\LocalDictation.exe"
Write-Host "dist\config.example.json was copied alongside it - rename it to config.json to customize settings before first run."
Write-Host "To run at login, create a shortcut to the exe in: shell:startup"
