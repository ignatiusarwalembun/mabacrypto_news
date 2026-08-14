@echo off
cd /d "%~dp0frontend"
start "Aurum Frontend" http://localhost:5500
py -m http.server 5500
pause
