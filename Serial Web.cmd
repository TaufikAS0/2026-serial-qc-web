@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Jalankan Setup.cmd dahulu.
  pause
  exit /b 1
)
if "%~1"=="" (
  ".venv\Scripts\python.exe" launcher.py open
) else (
  ".venv\Scripts\python.exe" launcher.py %*
)
