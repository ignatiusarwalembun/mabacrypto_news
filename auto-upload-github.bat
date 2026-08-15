@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
set "TARGET_REPO=https://github.com/ignatiusarwalembun/mabacrypto_news.git"

echo ==================================================
echo MabaCrypto News - Auto Upload GitHub
echo ==================================================
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo ERROR: Git belum terinstall atau tidak ada di PATH.
  echo Install Git for Windows, lalu jalankan file ini lagi.
  pause
  exit /b 1
)

rem Bersihkan state operasi Git lama TANPA mengembalikan working tree. Isi folder lokal tetap jadi snapshot terbaru.
if exist ".git\rebase-merge" git rebase --quit >nul 2>&1
if exist ".git\rebase-apply" git rebase --quit >nul 2>&1
if exist ".git\MERGE_HEAD" git merge --quit >nul 2>&1
if exist ".git\CHERRY_PICK_HEAD" git cherry-pick --quit >nul 2>&1
if exist ".git\REVERT_HEAD" git revert --quit >nul 2>&1

if not exist ".git" (
  echo Membuat repository Git lokal...
  git init
  if errorlevel 1 goto :error
)

git branch -M main >nul 2>&1

git remote get-url origin >nul 2>&1
if errorlevel 1 (
  git remote add origin "%TARGET_REPO%"
) else (
  git remote set-url origin "%TARGET_REPO%"
)
if errorlevel 1 goto :error

echo Scan semua file lokal...
git add -A
if errorlevel 1 goto :error

rem Buat snapshot lokal dulu. Ini menjaga isi folder saat ini sebagai versi yang harus menang.
git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Local snapshot before sync" >nul 2>&1
  if errorlevel 1 (
    echo ERROR: Commit gagal. Pastikan Git user.name dan user.email sudah diset.
    echo Contoh:
    echo   git config --global user.name "Nama Kamu"
    echo   git config --global user.email "email@kamu.com"
    pause
    exit /b 1
  )
)

echo Mengambil baseline remote main tanpa pull/rebase/merge...
git fetch origin main >nul 2>&1
if errorlevel 1 (
  echo Remote main belum ada atau repository masih kosong. Akan push snapshot lokal sebagai main.
) else (
  rem Pindahkan HEAD ke remote main, tetapi pertahankan index + working tree snapshot lokal.
  git reset --soft origin/main
  if errorlevel 1 goto :error
)

git add -A
if errorlevel 1 goto :error

git diff --cached --quiet
if errorlevel 1 (
  git commit -m "Update MabaCrypto News"
  if errorlevel 1 goto :error
) else (
  echo Tidak ada perubahan baru dibanding remote main.
)

echo Push ke GitHub main...
git push -u origin main
if errorlevel 1 (
  echo.
  echo ERROR: Push ditolak. Kemungkinan remote berubah setelah fetch atau login GitHub belum siap.
  echo Jalankan file ini sekali lagi. Script tidak menggunakan git pull --rebase atau merge.
  pause
  exit /b 1
)

echo.
echo SELESAI: Semua file sudah dipush ke:
echo %TARGET_REPO%
pause
exit /b 0

:error
echo.
echo ERROR: Proses Git berhenti. Baca pesan di atas, lalu jalankan BAT lagi setelah diperbaiki.
pause
exit /b 1
