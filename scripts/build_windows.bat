@echo off
setlocal

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"
set "ROOT_DIR=%CD%"

if "%PYTHON_BIN%"=="" (
  set "PYTHON_BIN=python"
)

if "%PYINSTALLER_CONFIG_DIR%"=="" (
  set "PYINSTALLER_CONFIG_DIR=%ROOT_DIR%\.pyinstaller"
)

if not exist "%PYINSTALLER_CONFIG_DIR%" (
  mkdir "%PYINSTALLER_CONFIG_DIR%"
)

"%PYTHON_BIN%" -m PyInstaller --noconfirm --clean packaging\pyinstaller.spec
if errorlevel 1 (
  exit /b %errorlevel%
)

echo Build completed.
echo Windows executable: %ROOT_DIR%\dist\ThesisFormatFixer.exe
echo PyInstaller cache dir: %PYINSTALLER_CONFIG_DIR%
