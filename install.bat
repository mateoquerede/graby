@echo off
setlocal EnableExtensions

cd /d "%~dp0"
title CotoBot - Instalacion automatica

echo ================================================
echo   CotoBot - Instalador one click (Windows)
echo ================================================
echo.

call :resolve_python
if errorlevel 1 goto :fail

echo [1/6] Verificando/creando entorno virtual...
if not exist ".venv\Scripts\python.exe" (
  call %PY_CMD% -m venv .venv
  if errorlevel 1 goto :fail
)

set "VENV_PY=.venv\Scripts\python.exe"

echo [2/6] Actualizando pip...
"%VENV_PY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [3/6] Instalando dependencias Python...
"%VENV_PY%" -m pip install -r shopping_copilot\src\requirements.txt
if errorlevel 1 goto :fail

echo [4/6] Instalando navegador Playwright (Firefox)...
"%VENV_PY%" -m playwright install firefox
if errorlevel 1 goto :fail

echo [5/6] Verificando Ollama...
call :ensure_ollama
if errorlevel 1 goto :fail

echo [6/6] Preparando configuracion inicial...
if not exist "shared\settings.json" (
  copy "shared\settings.example.json" "shared\settings.json" >nul
  echo   - Se creo shared\settings.json desde el ejemplo.
)

echo.
echo Instalacion completa.
echo Proximo paso: edita shared\settings.json con tus credenciales.
echo Luego ejecuta shopping.bat o consumption.bat.
echo.
pause
exit /b 0

:resolve_python
set "PY_CMD="

where py >nul 2>&1
if %errorlevel%==0 (
  set "PY_CMD=py -3"
  goto :python_ok
)

where python >nul 2>&1
if %errorlevel%==0 (
  set "PY_CMD=python"
  goto :python_ok
)

echo Python no detectado. Intentando instalar con winget...
where winget >nul 2>&1
if not %errorlevel%==0 (
  echo ERROR: winget no esta disponible. Instala App Installer de Microsoft Store y reintenta.
  exit /b 1
)

winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo ERROR: no se pudo instalar Python automaticamente.
  exit /b 1
)

where py >nul 2>&1
if %errorlevel%==0 (
  set "PY_CMD=py -3"
  goto :python_ok
)

where python >nul 2>&1
if %errorlevel%==0 (
  set "PY_CMD=python"
  goto :python_ok
)

if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  set "PY_CMD=%LocalAppData%\Programs\Python\Python312\python.exe"
  goto :python_ok
)

echo ERROR: Python fue instalado pero no se encontro en PATH. Cierra y abre la terminal, luego reintenta.
exit /b 1

:python_ok
echo Python detectado: %PY_CMD%
exit /b 0

:ensure_ollama
where ollama >nul 2>&1
if %errorlevel%==0 goto :ollama_pull

echo Ollama no detectado. Intentando instalar con winget...
where winget >nul 2>&1
if not %errorlevel%==0 (
  echo ERROR: winget no esta disponible y Ollama no esta instalado.
  exit /b 1
)

winget install --id Ollama.Ollama -e --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo ERROR: no se pudo instalar Ollama automaticamente.
  exit /b 1
)

:ollama_pull
echo Descargando modelo llama3 (puede tardar varios minutos)...
ollama pull llama3
if errorlevel 1 (
  echo ERROR: fallo la descarga del modelo llama3.
  exit /b 1
)

exit /b 0

:fail
echo.
echo La instalacion no se pudo completar.
echo Revisa el error anterior y vuelve a ejecutar install.bat.
echo.
pause
exit /b 1
