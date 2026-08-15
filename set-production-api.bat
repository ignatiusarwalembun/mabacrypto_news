@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"

echo ==================================================
echo MabaCrypto News - Set Production Railway API
echo ==================================================
echo.
set /p RAILWAY_URL=Masukkan domain Railway, contoh https://abc.up.railway.app : 

if "%RAILWAY_URL%"=="" (
  echo ERROR: Domain Railway tidak boleh kosong.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$p='frontend/config.js'; $u='%RAILWAY_URL%'.Trim().TrimEnd('/'); if($u.EndsWith('/api',[System.StringComparison]::OrdinalIgnoreCase)){$u=$u.Substring(0,$u.Length-4).TrimEnd('/')}; if(-not $u.StartsWith('https://',[System.StringComparison]::OrdinalIgnoreCase)){Write-Error 'Gunakan domain HTTPS Railway.'; exit 2}; $api=$u+'/api'; $c=Get-Content -Raw $p; $c=[regex]::Replace($c,'const PRODUCTION_API_BASE_URL = \"[^\"]+\";','const PRODUCTION_API_BASE_URL = \"'+$api+'\";'); Set-Content -Encoding UTF8 $p $c; Write-Host ''; Write-Host 'OK: Production API sekarang memakai:'; Write-Host $api"

if errorlevel 1 (
  echo.
  echo ERROR: Gagal mengubah frontend\config.js. Pastikan domain Railway benar.
  pause
  exit /b 1
)

echo.
echo Lanjutkan dengan double-click auto-upload-github.bat untuk push update.
pause
