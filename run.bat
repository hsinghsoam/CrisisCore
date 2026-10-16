@echo off
echo ========================================================
echo CrisisCore Emergency Coordination Platform
echo ========================================================
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)
python app.py
pause
