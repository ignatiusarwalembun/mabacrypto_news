@echo off
cd /d "%~dp0backend"
if not exist .env copy .env.example .env >nul
if not exist venv (
  py -3.12 -m venv venv
)
call venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
pause
