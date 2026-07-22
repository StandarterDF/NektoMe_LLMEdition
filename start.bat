@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
if "%1"=="" (
    python app.py
) else (
    python app.py %1
)
pause
