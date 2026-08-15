@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title MabaCrypto News - Local Launcher

set "ROOT=%CD%"
set "VENV=%ROOT%\.venv"
set "BACKEND_DIR=%ROOT%\backend"
set "FRONTEND_DIR=%ROOT%\frontend"
set "FRONTEND_PORT=8080"
set "BACKEND_PORT=5000"

echo.
echo ==============================================
echo        MabaCrypto News - Auto Run Local
echo ==============================================
echo.

if not exist "%BACKEND_DIR%\app.py" (
  echo [ERROR] backend\app.py tidak ditemukan.
  echo Pastikan BAT ini berada di root project MabaCrypto News.
  pause
  exit /b 1
)

if not exist "%FRONTEND_DIR%\index.html" (
  echo [ERROR] frontend\index.html tidak ditemukan.
  echo Pastikan BAT ini berada di root project MabaCrypto News.
  pause
  exit /b 1
)

set "PY_CMD="
where py >nul 2>&1
if not errorlevel 1 set "PY_CMD=py"
if not defined PY_CMD (
  where python >nul 2>&1
  if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
  echo [ERROR] Python tidak ditemukan.
  echo Install Python 3 terlebih dahulu lalu jalankan BAT ini lagi.
  pause
  exit /b 1
)

if not exist "%VENV%\Scripts\python.exe" (
  echo [SETUP] Membuat virtual environment .venv...
  %PY_CMD% -m venv "%VENV%"
  if errorlevel 1 (
    echo [ERROR] Gagal membuat virtual environment.
    pause
    exit /b 1
  )
)

set "VENV_PY=%VENV%\Scripts\python.exe"

echo [CHECK] Memeriksa dependency backend...
"%VENV_PY%" -c "import flask, flask_cors, feedparser, apscheduler, requests" >nul 2>&1
if errorlevel 1 (
  echo [SETUP] Dependency belum lengkap. Menginstall requirements...
  "%VENV_PY%" -m pip install --upgrade pip
  if errorlevel 1 goto :pip_error

  "%VENV_PY%" -m pip install -r "%BACKEND_DIR%\requirements.txt"
  if errorlevel 1 goto :pip_error
) else (
  echo [OK] Dependency backend siap.
)

set "PORT=%BACKEND_PORT%"
set "CORS_ORIGINS=*"
if not defined NEWS_REFRESH_MINUTES set "NEWS_REFRESH_MINUTES=20"
if not defined DATABASE_PATH set "DATABASE_PATH=%BACKEND_DIR%\data\news.db"

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr "LISTENING" 2^>nul') do set "BACKEND_PID=%%P"
if defined BACKEND_PID (
  echo [INFO] Port %BACKEND_PORT% sudah dipakai. Backend mungkin sudah aktif.
) else (
  echo [START] Menyalakan backend di http://localhost:%BACKEND_PORT% ...
  start "MabaCrypto Backend" cmd /k "cd /d ""%BACKEND_DIR%"" && set PORT=%BACKEND_PORT% && set CORS_ORIGINS=* && set DATABASE_PATH=%DATABASE_PATH% && set NEWS_REFRESH_MINUTES=%NEWS_REFRESH_MINUTES% && ""%VENV_PY%"" app.py"
)

set "FRONTEND_PID="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":%FRONTEND_PORT% " ^| findstr "LISTENING" 2^>nul') do set "FRONTEND_PID=%%P"
if defined FRONTEND_PID (
  echo [INFO] Port %FRONTEND_PORT% sudah dipakai. Frontend mungkin sudah aktif.
) else (
  echo [START] Menyalakan frontend di http://localhost:%FRONTEND_PORT% ...
  start "MabaCrypto Frontend" cmd /k "cd /d ""%ROOT%"" && ""%VENV_PY%"" -m http.server %FRONTEND_PORT% --directory frontend"
)

echo.
echo ==============================================
echo Backend : http://localhost:%BACKEND_PORT%
echo Health  : http://localhost:%BACKEND_PORT%/api/health
echo Frontend: http://localhost:%FRONTEND_PORT%
echo ==============================================
echo.
echo Browser akan dibuka otomatis.
echo Tutup window Backend dan Frontend untuk menghentikan server.

timeout /t 3 /nobreak >nul
start "" "http://localhost:%FRONTEND_PORT%"

exit /b 0

:pip_error
echo.
echo [ERROR] Gagal menginstall dependency Python.
echo Cek koneksi internet lalu jalankan auto-run-local.bat lagi.
pause
exit /b 1
