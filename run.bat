@echo off
setlocal EnableExtensions

cd /d "%~dp0"
title CotoBot - Run

if not exist ".venv\Scripts\python.exe" (
  echo Entorno no detectado. Ejecutando instalacion inicial...
  call install.bat
  if errorlevel 1 (
    echo.
    echo ERROR: la instalacion fallo. No se puede continuar.
    pause
    exit /b 1
  )
)

echo Verificando credenciales de Coto...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ensure_coto_credentials.ps1"
if errorlevel 1 (
  echo.
  echo ERROR: no se pudieron verificar/guardar las credenciales.
  pause
  exit /b 1
)

call shopping.bat
exit /b %errorlevel%
