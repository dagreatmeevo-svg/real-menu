@echo off
rem Drag a folder of photos onto this file. It asks for the layer name, then builds scans\<name>\<name>.glb
if "%~1"=="" (
  echo Drag a folder of photos onto scan.bat
  pause
  exit /b 1
)
set /p NAME=Layer name (e.g. patty, bun_top):
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scan.ps1" -Photos "%~1" -Name "%NAME%"
pause
