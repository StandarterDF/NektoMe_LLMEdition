@echo off
chcp 65001 >nul
cd /d "%~dp0"
call venv\Scripts\activate.bat
python app.py 12345
pause
