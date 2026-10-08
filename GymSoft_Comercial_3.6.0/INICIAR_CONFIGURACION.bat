@echo off
setlocal
cd /d "%~dp0"
call PREPARAR_PYTHON.bat
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
".venv\Scripts\python.exe" configurar_proveedor.py
if errorlevel 1 goto :error
pause
exit /b 0
:error
echo No se completo la preparacion. Revisa el mensaje anterior y reintenta.
pause
exit /b 1
