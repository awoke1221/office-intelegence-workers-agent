# Run the project using the local .venv and install requirements only when needed.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $projectRoot '.venv'
$pythonExe = Join-Path $venvPath 'Scripts\python.exe'

if (-not (Test-Path $venvPath)) {
    Write-Host 'Creating project virtual environment (.venv)...'
    python -m venv $venvPath
}

if (-not (Test-Path $pythonExe)) {
    Write-Error "Could not locate .venv Python interpreter at $pythonExe"
    exit 1
}

Write-Host "Using project virtual environment: $pythonExe"

try {
    & $pythonExe -c "import streamlit" | Out-Null
} catch {
    Write-Host 'Installing missing packages from requirements.txt...'
    & $pythonExe -m pip install --upgrade pip | Out-Null
    & $pythonExe -m pip install -r (Join-Path $projectRoot 'requirements.txt')
}

Write-Host 'Starting Streamlit app...'
& $pythonExe -m streamlit run (Join-Path $projectRoot 'streamlit_app.py')
