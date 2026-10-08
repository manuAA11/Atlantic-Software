@echo off
setlocal
cd /d "%~dp0"
call PREPARAR_PYTHON.bat
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :error
call PREPARAR_PRUEBAS.bat
if errorlevel 1 goto :error
".venv\Scripts\python.exe" build_windows.py
if errorlevel 1 goto :error
echo Instalador de ZTATTUZ generado en salida. Copialo al equipo del gimnasio.
pause
exit /b 0
:error
echo La compilacion no termino. Revisa el error anterior; no entregues archivos incompletos.
pause
exit /b 1
