@echo off
setlocal

cd /d "%~dp0"
title Anz Clicker - Create Update

echo Anz Clicker Release Creator
echo ===========================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0packaging\create_release.ps1"
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
    echo Release creator finished.
) else (
    echo Release creator stopped with an error.
)

if not defined ANZ_RELEASE_NO_PAUSE pause
exit /b %EXIT_CODE%
