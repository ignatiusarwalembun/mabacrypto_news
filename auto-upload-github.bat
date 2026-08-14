@echo off
setlocal EnableExtensions EnableDelayedExpansion
title MABACRYPTO NEWS - GitHub Uploader v1.5.5

cd /d "%~dp0"

set "REPO_URL=https://github.com/ignatiusarwalembun/mabacrypto_news.git"
set "BRANCH=main"
set "DEFAULT_COMMIT=Update mabacrypto_news"

echo.
echo ============================================
echo   MABACRYPTO NEWS - AUTO GITHUB UPLOADER
echo   VERSION 1.5.5
echo ============================================
echo.

where git >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Git tidak ditemukan.
    pause
    exit /b 1
)

if not exist ".git" (
    echo [1/8] Membuat repository Git lokal...
    git init
    if errorlevel 1 goto :error
) else (
    echo [1/8] Repository Git lokal sudah ada.
)

echo [2/8] Membersihkan state Git yang belum selesai...

set "REBASE_ACTIVE="
for /f "delims=" %%P in ('git rev-parse --git-path rebase-merge 2^>nul') do (
    if exist "%%P" set "REBASE_ACTIVE=1"
)
if not defined REBASE_ACTIVE (
    for /f "delims=" %%P in ('git rev-parse --git-path rebase-apply 2^>nul') do (
        if exist "%%P" set "REBASE_ACTIVE=1"
    )
)

if defined REBASE_ACTIVE (
    echo [INFO] Rebase lama terdeteksi. Membatalkan rebase...
    git rebase --abort
    if errorlevel 1 goto :error
)

git rev-parse -q --verify MERGE_HEAD >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Merge lama terdeteksi. Membatalkan merge...
    git merge --abort
    if errorlevel 1 goto :error
)

echo [3/8] Menyiapkan branch %BRANCH%...
set "CURRENT_BRANCH="
for /f "delims=" %%B in ('git symbolic-ref --quiet --short HEAD 2^>nul') do set "CURRENT_BRANCH=%%B"

if not defined CURRENT_BRANCH (
    git rev-parse --verify HEAD >nul 2>&1
    if errorlevel 1 (
        git symbolic-ref HEAD refs/heads/%BRANCH%
        if errorlevel 1 goto :error
    ) else (
        git show-ref --verify --quiet refs/heads/%BRANCH%
        if errorlevel 1 (
            git switch -c %BRANCH%
            if errorlevel 1 goto :error
        ) else (
            git switch %BRANCH%
            if errorlevel 1 goto :error
        )
    )
) else (
    if /I not "!CURRENT_BRANCH!"=="%BRANCH%" (
        git show-ref --verify --quiet refs/heads/%BRANCH%
        if errorlevel 1 (
            git branch -m %BRANCH%
            if errorlevel 1 goto :error
        ) else (
            git switch %BRANCH%
            if errorlevel 1 goto :error
        )
    )
)

echo [4/8] Memeriksa remote origin...
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    git remote add origin "%REPO_URL%"
    if errorlevel 1 goto :error
) else (
    for /f "delims=" %%R in ('git remote get-url origin') do set "CURRENT_REMOTE=%%R"
    if /I not "!CURRENT_REMOTE!"=="%REPO_URL%" (
        git remote set-url origin "%REPO_URL%"
        if errorlevel 1 goto :error
    )
)

echo [5/8] Menambahkan semua perubahan project...
git add -A
if errorlevel 1 goto :error

git diff --cached --quiet
if not errorlevel 1 (
    echo [INFO] Tidak ada perubahan lokal baru untuk di-commit.
) else (
    echo.
    set "COMMIT_MSG="
    set /p "COMMIT_MSG=Commit message, tekan Enter untuk default: "
    if not defined COMMIT_MSG set "COMMIT_MSG=%DEFAULT_COMMIT%"

    echo [6/8] Membuat commit lokal...
    git commit -m "!COMMIT_MSG!"
    if errorlevel 1 goto :error
)

echo [7/8] Sinkronisasi riwayat GitHub tanpa rebase...
git fetch origin %BRANCH% >nul 2>&1

git show-ref --verify --quiet refs/remotes/origin/%BRANCH%
if not errorlevel 1 (
    git merge-base --is-ancestor origin/%BRANCH% HEAD >nul 2>&1
    if errorlevel 1 (
        echo [INFO] Riwayat GitHub berbeda. Menghubungkan riwayat dan mempertahankan isi project lokal...
        git merge -s ours origin/%BRANCH% --allow-unrelated-histories -m "Sync GitHub history with local mabacrypto_news"
        if errorlevel 1 goto :error
    ) else (
        echo [INFO] Riwayat lokal sudah mencakup GitHub.
    )
) else (
    echo [INFO] Branch remote belum ada. Akan dibuat saat push.
)

echo [8/8] Upload ke GitHub...
git push -u origin %BRANCH%
if errorlevel 1 goto :error

echo.
echo ============================================
echo   SUCCESS - PROJECT SUDAH DIUPLOAD
echo   VERSION 1.5.5
echo ============================================
echo https://github.com/ignatiusarwalembun/mabacrypto_news
echo.
pause
exit /b 0

:error
echo.
echo ============================================
echo   GAGAL MENJALANKAN GIT COMMAND
echo   VERSION 1.5.5
echo ============================================
echo Lihat pesan Git tepat di atas.
echo.
pause
exit /b 1
