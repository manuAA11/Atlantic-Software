@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3.13 -m venv .venv
  if errorlevel 1 goto :error
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
".venv\Scripts\python.exe" configurar_proveedor.py
pause
exit /b 0
:error
echo No se completo la preparacion. Instala Python 3.13 de 64 bits y reintenta.
pause
exit /b 1
