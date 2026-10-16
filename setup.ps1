Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Setting up CrisisCore Environment" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

python -m venv venv
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
    exit $LASTEXITCODE
}

.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed_data.py

Write-Host "========================================================" -ForegroundColor Green
Write-Host "CrisisCore setup completed successfully!" -ForegroundColor Green
Write-Host "Run '.\run.ps1' to start the application." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
