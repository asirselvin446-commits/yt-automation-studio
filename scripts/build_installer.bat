@echo off
title YT Automation Studio - Build Installer
echo ===============================================================
echo Building YT Automation Studio Desktop Software & Inno Installer
echo ===============================================================

cd /d "%~dp0\.."
call .venv\Scripts\activate.bat
python scripts\build_software.py

pause
