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

if not exist "%ROOT_DIR%\dist\ThesisFormatFixer\ThesisFormatFixer.exe" (
  echo Build failed: missing Windows executable: %ROOT_DIR%\dist\ThesisFormatFixer\ThesisFormatFixer.exe
  exit /b 1
)

if not exist "%ROOT_DIR%\dist\ThesisFormatFixer\rules" (
  echo Build failed: bundled rules directory missing: %ROOT_DIR%\dist\ThesisFormatFixer\rules
  exit /b 1
)

if not exist "%ROOT_DIR%\dist\ThesisFormatFixer\rules\FORMAT_RULEBOOK_v1.md" (
  echo Build failed: bundled rulebook missing: %ROOT_DIR%\dist\ThesisFormatFixer\rules\FORMAT_RULEBOOK_v1.md
  exit /b 1
)

echo Build completed.
echo Windows dist dir: %ROOT_DIR%\dist\ThesisFormatFixer
echo Windows executable: %ROOT_DIR%\dist\ThesisFormatFixer\ThesisFormatFixer.exe
echo Bundled rules dir: %ROOT_DIR%\dist\ThesisFormatFixer\rules
echo PyInstaller cache dir: %PYINSTALLER_CONFIG_DIR%
