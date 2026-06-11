# Start backend + frontend locally for gas-analytics.
$ErrorActionPreference = "Stop"

Write-Host "Starting backend on :8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit","-Command","Set-Location backend; if (-not (Test-Path .venv)) { python -m venv .venv }; .\.venv\Scripts\Activate.ps1; pip install -q -r requirements.txt; uvicorn app.main:app --reload --port 8000"

Start-Sleep -Seconds 2

Write-Host "Starting frontend on :3000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit","-Command","Set-Location frontend; if (-not (Test-Path node_modules)) { npm install }; npm run dev"

Write-Host "Backend:  http://localhost:8000/docs"
Write-Host "Frontend: http://localhost:3000"
