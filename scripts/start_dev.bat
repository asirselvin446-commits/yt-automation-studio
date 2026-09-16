@echo off
title YT Automation Studio - Dev Launcher
echo ===============================================================
echo Launching YT Automation Studio Desktop Application
echo ===============================================================

cd /d "%~dp0\.."
call .venv\Scripts\activate.bat
python desktop_app.py

pause
