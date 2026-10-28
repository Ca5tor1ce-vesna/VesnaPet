@echo off
setlocal
cd /d "%~dp0"

set "PY="
set "PYW="
py -3 --version >nul 2>nul && set "PY=py -3" && set "PYW=pyw -3"
if not defined PY python --version >nul 2>nul && set "PY=python" && set "PYW=pythonw"
if not defined PY goto nopython

if exist ".deps_ok" goto start

echo [VesnaPet] First run, installing PySide6 - please wait a few minutes...
%PY% -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 goto trydefault
goto depsok

:trydefault
echo [VesnaPet] Mirror failed, trying default PyPI...
%PY% -m pip install -r requirements.txt
if errorlevel 1 goto pipfail

:depsok
echo ok> ".deps_ok"

:start
rem test import first so errors are visible
%PY% -c "import PySide6" 2>nul
if errorlevel 1 goto importfail
start "" %PYW% "%~dp0main.py"
exit /b 0

:nopython
echo [VesnaPet] Python 3 not found. Please install it from https://www.python.org/
pause
exit /b 1

:pipfail
echo [VesnaPet] pip install failed. Please check your network.
pause
exit /b 1

:importfail
echo [VesnaPet] PySide6 is not installed correctly. Deleting marker, please run again.
del ".deps_ok" 2>nul
pause
exit /b 1
