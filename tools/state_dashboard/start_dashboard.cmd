@echo off
rem Development state dashboard launcher (desktop shortcut target)
setlocal
cd /d "%~dp0..\.."
where python >nul 2>nul
if errorlevel 1 (
  py -3 tools\state_dashboard\serve.py %* --open
) else (
  python tools\state_dashboard\serve.py %* --open
)
