@echo off
setlocal
cd /d "%~dp0"
call PREPARAR_PYTHON.bat
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error
call PREPARAR_PRUEBAS.bat
if errorlevel 1 goto :error
".venv\Scripts\python.exe" run_validation.py
if errorlevel 1 goto :error
echo Simulacion completada. Consulta salida\validacion\RESUMEN_PRUEBAS.txt
pause
exit /b 0
:error
echo La validacion no termino. Copia el error o revisa salida\validacion.
pause
exit /b 1
