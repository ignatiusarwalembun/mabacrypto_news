@echo off
cd /d "%~dp0"
start "Aurum Backend" cmd /k start-backend.bat
ping 127.0.0.1 -n 4 >nul
start "Aurum Frontend" cmd /k start-frontend.bat
exit
