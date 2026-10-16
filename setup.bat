@echo off
echo ========================================================
echo Setting up CrisisCore Environment
echo ========================================================

python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment. Ensure Python 3.10+ is installed.
    exit /b %errorlevel%
)

call venv\Scripts\activate.bat
pip install -r requirements.txt
python seed_data.py

echo ========================================================
echo CrisisCore setup completed successfully!
echo Run 'run.bat' to start the application.
echo ========================================================
pause
