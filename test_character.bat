@echo off
chcp 1251 >nul
"%~dp0venv\Scripts\python" "%~dp0generators\test_character.py"
pause
