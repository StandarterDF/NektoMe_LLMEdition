@echo off
chcp 1251 >nul
"%~dp0venv\Scripts\python" "%~dp0test_character.py"
pause
