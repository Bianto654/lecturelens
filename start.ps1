# LectureLens (Python Stack) One-Click Local Launcher
# Starts FastAPI + WebSockets on :8000 and Streamlit UI on :8501

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Py)) {
    Write-Error "Virtualenv not found at $Py. Run: python -m venv .venv && .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}

Write-Host "Starting FastAPI + WebSockets backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
$backend = Start-Process -FilePath $Py -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $Root -PassThru

Start-Sleep -Seconds 2
Write-Host "Starting Streamlit frontend on http://localhost:8501 ..." -ForegroundColor Green
try {
    Set-Location $Root
    & $Py -m streamlit run streamlit_app.py --server.port 8501 --server.address 0.0.0.0
} finally {
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force
    }
}
