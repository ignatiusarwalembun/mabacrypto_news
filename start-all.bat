@echo off
cd /d "%~dp0"
start "MabaCrypto News Backend" cmd /k start-backend.bat
ping 127.0.0.1 -n 4 >nul
start "MabaCrypto News Frontend" cmd /k start-frontend.bat
exit
