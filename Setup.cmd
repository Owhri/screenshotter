@echo off
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.12 from python.org, then run Setup.cmd again.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
)
.venv\Scripts\python.exe -m pip install .
if errorlevel 1 goto failed
echo Setup complete. Run Configure.cmd to save your API key, then run Start.cmd.
pause
exit /b 0
:failed
echo Setup failed. Read the error above.
pause
exit /b 1
