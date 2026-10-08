@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
call PREPARAR_PYTHON.bat
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto :error
exit /b 0

:error
echo No se pudo iniciar el programa. Revisa el mensaje anterior.
pause
exit /b 1
