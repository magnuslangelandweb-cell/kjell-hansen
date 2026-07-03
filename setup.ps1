# Sets up the local dictation app: creates a venv, installs dependencies,
# and prepares config.json. Run from the project root in PowerShell.
#   powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"

function Get-PythonCommand {
    foreach ($cmd in @("python", "py")) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            return $cmd
        }
    }
    throw "Python 3.10+ not found on PATH. Install it from https://www.python.org/downloads/ and re-run this script."
}

$python = Get-PythonCommand
$versionOutput = & $python --version
Write-Host "Using $versionOutput"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    & $python -m venv .venv
}

$venvPython = ".\.venv\Scripts\python.exe"

Write-Host "Upgrading pip..."
& $venvPython -m pip install --upgrade pip | Out-Null

Write-Host "Installing dependencies (this can take a few minutes on first run)..."
& $venvPython -m pip install -r requirements.txt

if (-not (Test-Path "config.json")) {
    Copy-Item "config.example.json" "config.json"
    Write-Host "Created config.json from config.example.json"
}

Write-Host ""
Write-Host "Setup complete."
Write-Host "Run the app with:"
Write-Host "  .\.venv\Scripts\python.exe src\main.py"
Write-Host ""
Write-Host "The Whisper model downloads automatically on first run (small.en by default)."
Write-Host "Hold Right Ctrl to record, release to transcribe and paste into the focused window."
