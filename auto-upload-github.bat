@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ================================================
echo  MabaCrypto News - GitHub Auto Upload
echo ================================================

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git tidak ditemukan.
  echo Install Git for Windows lalu jalankan BAT ini lagi.
  pause
  exit /b 1
)

if not exist ".git" (
  echo [INFO] Repository Git belum ada. Membuat repository baru...
  git init
  if errorlevel 1 goto :git_error
)

rem Bersihkan state merge/rebase lama supaya tidak mengunci repository.
git rebase --abort >nul 2>&1
git merge --abort >nul 2>&1
git cherry-pick --abort >nul 2>&1

set "TARGET_ORIGIN=https://github.com/ignatiusarwalembun/mabacrypto_news.git"
for /f "delims=" %%i in ('git remote get-url origin 2^>nul') do set "CURRENT_ORIGIN=%%i"

if not defined CURRENT_ORIGIN (
  echo [INFO] Menambahkan origin...
  git remote add origin "%TARGET_ORIGIN%"
) else if /I not "%CURRENT_ORIGIN%"=="%TARGET_ORIGIN%" (
  echo [INFO] Origin salah. Memperbaiki origin...
  git remote set-url origin "%TARGET_ORIGIN%"
)

rem Pastikan identitas commit tersedia di repository ini.
for /f "delims=" %%i in ('git config user.name 2^>nul') do set "GIT_NAME=%%i"
if not defined GIT_NAME git config user.name "ignatiusarwalembun"
for /f "delims=" %%i in ('git config user.email 2^>nul') do set "GIT_EMAIL=%%i"
if not defined GIT_EMAIL git config user.email "ignatiusarwalembun@users.noreply.github.com"

echo [INFO] Mengambil baseline remote main...
git fetch origin main
set "FETCH_RESULT=%ERRORLEVEL%"

rem Nama branch lokal selalu main, tanpa mengubah isi folder kerja.
git branch -M main >nul 2>&1

rem Jika remote main ada, jadikan itu baseline index/HEAD. --mixed menjaga snapshot
rem file lokal tetap utuh, jadi folder lokal tetap menjadi versi terbaru.
git show-ref --verify --quiet refs/remotes/origin/main
if not errorlevel 1 (
  git reset --mixed origin/main
  if errorlevel 1 goto :git_error
) else (
  if not "%FETCH_RESULT%"=="0" echo [INFO] Remote main belum ada atau repository masih kosong.
)

echo [INFO] Scan semua file lokal...
git add -A
if errorlevel 1 goto :git_error

git diff --cached --quiet
if not errorlevel 1 (
  echo [OK] Tidak ada perubahan baru untuk di-upload.
  pause
  exit /b 0
)

for /f "tokens=1-3 delims=/ " %%a in ("%date%") do set "DATESTAMP=%%a-%%b-%%c"
set "TIMESTAMP=%time: =0%"
git commit -m "update MabaCrypto News %DATESTAMP% %TIMESTAMP%"
if errorlevel 1 goto :git_error

echo [INFO] Push ke GitHub main...
git push -u origin main
if not errorlevel 1 goto :success

echo [WARN] Push pertama gagal. Remote mungkin berubah. Mencoba sekali lagi dari baseline terbaru...
git fetch origin main
if errorlevel 1 goto :git_error
git reset --mixed origin/main
if errorlevel 1 goto :git_error
git add -A
git diff --cached --quiet
if not errorlevel 1 goto :success
git commit -m "update MabaCrypto News retry %DATESTAMP% %TIMESTAMP%"
if errorlevel 1 goto :git_error
git push -u origin main
if errorlevel 1 goto :git_error

:success
echo.
echo [OK] Semua file berhasil di-commit dan push ke GitHub.
echo Repository: %TARGET_ORIGIN%
pause
exit /b 0

:git_error
echo.
echo [ERROR] Proses Git gagal.
echo Cek pesan di atas. Pastikan login GitHub/Git Credential Manager aktif
echo dan koneksi internet tersedia.
pause
exit /b 1
