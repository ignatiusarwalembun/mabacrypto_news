@echo off
setlocal EnableExtensions EnableDelayedExpansion
title MabaCrypto News - Safe Auto Upload GitHub

cd /d "%~dp0"

set "REPO_URL=https://github.com/ignatiusarwalembun/mabacrypto_news.git"
set "BRANCH=main"

echo.
echo ============================================
echo   MABACRYPTO NEWS - SAFE AUTO UPLOADER
echo ============================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git tidak ditemukan.
    echo Install Git for Windows terlebih dahulu.
    pause
    exit /b 1
)

REM Bersihkan state rebase/merge lama agar BAT bisa dipakai lagi.
if exist ".git\rebase-merge" (
    echo [INFO] Rebase lama terdeteksi. Membatalkan rebase...
    git rebase --abort >nul 2>&1
)
if exist ".git\rebase-apply" (
    echo [INFO] Rebase lama terdeteksi. Membatalkan rebase...
    git rebase --abort >nul 2>&1
)
if exist ".git\MERGE_HEAD" (
    echo [INFO] Merge lama terdeteksi. Membatalkan merge...
    git merge --abort >nul 2>&1
)

if not exist ".git" (
    echo [1/8] Membuat repository Git lokal...
    git init
    if errorlevel 1 goto :error
) else (
    echo [1/8] Repository Git lokal ditemukan.
)

git config user.name >nul 2>&1
if errorlevel 1 (
    set /p "GIT_NAME=Masukkan nama GitHub / nama commit: "
    if not "!GIT_NAME!"=="" git config user.name "!GIT_NAME!"
)

git config user.email >nul 2>&1
if errorlevel 1 (
    set /p "GIT_EMAIL=Masukkan email GitHub: "
    if not "!GIT_EMAIL!"=="" git config user.email "!GIT_EMAIL!"
)

git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [2/8] Menambahkan remote GitHub...
    git remote add origin "%REPO_URL%"
    if errorlevel 1 goto :error
) else (
    for /f "delims=" %%R in ('git remote get-url origin') do set "CURRENT_REMOTE=%%R"
    if /I not "!CURRENT_REMOTE!"=="%REPO_URL%" (
        echo [2/8] Mengubah remote origin...
        git remote set-url origin "%REPO_URL%"
        if errorlevel 1 goto :error
    ) else (
        echo [2/8] Remote origin sudah benar.
    )
)

echo [3/8] Mengambil kondisi terbaru dari GitHub...
git fetch origin %BRANCH%
if errorlevel 1 (
    echo [INFO] Remote branch mungkin masih kosong. Lanjut sebagai upload pertama.
    goto :firstpush
)

echo [4/8] Menjadikan GitHub sebagai baseline tanpa menimpa file lokal...
REM Reset index/HEAD ke remote, tapi WORKTREE LOKAL TETAP DIPERTAHANKAN.
git reset --mixed origin/%BRANCH%
if errorlevel 1 goto :error

goto :stage

:firstpush
echo [4/8] Menyiapkan branch upload pertama...
git branch -M %BRANCH%
if errorlevel 1 goto :error

:stage
echo [5/8] Scan seluruh file project lokal...
git add -A
if errorlevel 1 goto :error

git diff --cached --quiet
if not errorlevel 1 (
    echo.
    echo [INFO] Tidak ada perubahan dibanding GitHub.
    echo Project sudah sinkron.
    goto :success
)

set "COMMIT_MSG="
echo.
set /p "COMMIT_MSG=Commit message [Update MabaCrypto News]: "
if "!COMMIT_MSG!"=="" set "COMMIT_MSG=Update MabaCrypto News"

echo [6/8] Membuat commit dari snapshot folder lokal...
git commit -m "!COMMIT_MSG!"
if errorlevel 1 goto :error

echo [7/8] Memastikan branch main...
git branch -M %BRANCH%
if errorlevel 1 goto :error

echo [8/8] Upload ke GitHub...
git push -u origin %BRANCH%
if errorlevel 1 goto :error

:success
echo.
echo ============================================
echo   SUCCESS - GITHUB SUDAH TERUPDATE
echo ============================================
echo https://github.com/ignatiusarwalembun/mabacrypto_news
echo.
echo Workflow:
echo Extract versi baru ^> klik BAT ^> commit ^> selesai.
echo.
pause
exit /b 0

:error
echo.
echo ============================================
echo   GAGAL MENJALANKAN AUTO UPLOAD
echo ============================================
echo Cek error Git di atas.
echo Jika diminta login GitHub, selesaikan login lewat browser.
echo.
pause
exit /b 1
