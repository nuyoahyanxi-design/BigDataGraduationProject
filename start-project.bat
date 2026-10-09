@echo off
setlocal
rem First launch configures Git-ignored .env.local; following launches reuse it.
powershell.exe -NoProfile -File "%~dp0scripts\start-project.ps1" %*
exit /b %errorlevel%
