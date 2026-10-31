@echo off
setlocal
cd /d "%~dp0"
set "PY="
set "PYW="
rem Prefer 3.12: default py may be 3.15 which lacks PySide6/openai wheels
py -3.12 --version >nul 2>nul && set "PY=py -3.12" && set "PYW=pyw -3.12"
if not defined PY py -3 --version >nul 2>nul && set "PY=py -3" && set "PYW=pyw -3"
if not defined PY python --version >nul 2>nul && set "PY=python" && set "PYW=pythonw"
if not defined PY goto nopython
%PY% -c "import PySide6, openai" 2>nul
if errorlevel 1 (
  echo [VesnaDLC] installing openai / PySide6 ...
  %PY% -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  if errorlevel 1 %PY% -m pip install -r requirements.txt
)
start "" %PYW% "%~dp0main.py"
exit /b 0
:nopython
echo Python 3 not found.
pause
exit /b 1
