@echo off
setlocal EnableExtensions EnableDelayedExpansion
title Auto Upload GitHub - mabacrypto_news

cd /d "%~dp0"

set "REPO_URL=https://github.com/ignatiusarwalembun/mabacrypto_news.git"
set "BRANCH=main"

echo.
echo ============================================
echo   MABACRYPTO NEWS - AUTO GITHUB UPLOADER
echo ============================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git tidak ditemukan.
    echo Install Git for Windows terlebih dahulu.
    pause
    exit /b 1
)

if not exist ".git" (
    echo [1/7] Membuat repository Git lokal...
    git init
    if errorlevel 1 goto :error
) else (
    echo [1/7] Repository Git lokal sudah ada.
)

git config user.name >nul 2>&1
if errorlevel 1 (
    echo.
    set /p "GIT_NAME=Masukkan nama GitHub / nama commit: "
    if not "!GIT_NAME!"=="" git config user.name "!GIT_NAME!"
)

git config user.email >nul 2>&1
if errorlevel 1 (
    echo.
    set /p "GIT_EMAIL=Masukkan email GitHub: "
    if not "!GIT_EMAIL!"=="" git config user.email "!GIT_EMAIL!"
)

echo [2/7] Menyiapkan branch %BRANCH%...
git branch -M %BRANCH%
if errorlevel 1 goto :error

git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo [3/7] Menambahkan remote GitHub...
    git remote add origin "%REPO_URL%"
    if errorlevel 1 goto :error
) else (
    for /f "delims=" %%R in ('git remote get-url origin') do set "CURRENT_REMOTE=%%R"
    if /I not "!CURRENT_REMOTE!"=="%REPO_URL%" (
        echo [3/7] Mengubah remote origin ke mabacrypto_news...
        git remote set-url origin "%REPO_URL%"
        if errorlevel 1 goto :error
    ) else (
        echo [3/7] Remote origin sudah benar.
    )
)

echo [4/7] Scan seluruh file project...
git add -A
if errorlevel 1 goto :error

git diff --cached --quiet
if not errorlevel 1 (
    echo.
    echo [INFO] Tidak ada perubahan baru untuk di-commit.
    goto :push
)

echo.
set "COMMIT_MSG="
set /p "COMMIT_MSG=Commit message [Update mabacrypto_news]: "
if "!COMMIT_MSG!"=="" set "COMMIT_MSG=Update mabacrypto_news"

echo [5/7] Membuat commit...
git commit -m "!COMMIT_MSG!"
if errorlevel 1 goto :error

:push
echo [6/7] Sinkronisasi dengan GitHub...

git ls-remote --exit-code --heads origin %BRANCH% >nul 2>&1
if not errorlevel 1 (
    git pull --rebase origin %BRANCH%
    if errorlevel 1 (
        echo.
        echo [ERROR] Pull/rebase gagal karena kemungkinan conflict.
        echo Selesaikan conflict terlebih dahulu lalu jalankan BAT ini lagi.
        pause
        exit /b 1
    )
)

echo [7/7] Upload ke GitHub...
git push -u origin %BRANCH%
if errorlevel 1 goto :error

echo.
echo ============================================
echo   SUCCESS - PROJECT SUDAH DIUPLOAD
echo ============================================
echo https://github.com/ignatiusarwalembun/mabacrypto_news
echo.
pause
exit /b 0

:error
echo.
echo ============================================
echo   GAGAL MENJALANKAN GIT COMMAND
echo ============================================
echo Cek pesan error Git di atas.
echo Jika GitHub meminta login, login melalui
echo Git Credential Manager / browser lalu ulangi.
echo.
pause
exit /b 1
