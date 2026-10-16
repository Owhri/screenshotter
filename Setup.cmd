@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install

rem The Python launcher is optional. Also try PATH and standard install folders.
rem A custom executable can be supplied as: Setup.cmd "D:\Python\python.exe"
set "SCREENSHOTTER_READY="
set "SCREENSHOTTER_BROKEN="
if not "%~1"=="" call :try_python "%~1"
call :try_python py -3.12
call :try_python python
call :try_python python3
call :try_python py -3.14
call :try_python py -3.13
call :try_python py -3.11
call :try_python py
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*" "%LOCALAPPDATA%\Python\pythoncore-*" "%ProgramFiles%\Python*" "%SystemDrive%\Python3*") do call :try_python "%%~fD\python.exe"
if defined SCREENSHOTTER_BROKEN goto failed
if not defined SCREENSHOTTER_READY goto not_found

:install
".venv\Scripts\python.exe" -c "import struct,sys; sys.exit(0 if sys.implementation.name == 'cpython' and (3,11) <= sys.version_info[:2] < (3,15) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
if errorlevel 1 goto bad_venv
".venv\Scripts\python.exe" -m pip install .
if errorlevel 1 goto failed
echo Setup complete. Run Configure.cmd to save your API key, then run Start.cmd.
pause
exit /b 0

:try_python
if defined SCREENSHOTTER_READY exit /b 0
if defined SCREENSHOTTER_BROKEN exit /b 0
%* -c "import struct,sys; sys.exit(0 if sys.implementation.name == 'cpython' and (3,11) <= sys.version_info[:2] < (3,15) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
if errorlevel 1 exit /b 0
echo Found compatible Python:
%* -c "import sys; print(sys.executable); print(sys.version)"
%* -m venv .venv
if errorlevel 1 (
  set "SCREENSHOTTER_BROKEN=1"
  exit /b 0
)
set "SCREENSHOTTER_READY=1"
exit /b 0

:not_found
echo Could not find 64-bit CPython 3.11, 3.12, 3.13, or 3.14.
echo Python may be installed without a launcher or outside the standard folders.
echo If you know its location, run: Setup.cmd "C:\path\to\python.exe"
echo Otherwise install 64-bit Python 3.12 from https://www.python.org/downloads/
echo The Python launcher is optional. Then run Setup.cmd again.
pause
exit /b 1

:bad_venv
echo The existing .venv is broken or uses an unsupported Python version or architecture.
echo Remove only this app's .venv folder, then run Setup.cmd again.
pause
exit /b 1

:failed
echo Setup failed. Read the error above.
pause
exit /b 1
