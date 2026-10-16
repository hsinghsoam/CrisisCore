Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "CrisisCore Emergency Coordination Platform" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

if (Test-Path ".\venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
}
python app.py
