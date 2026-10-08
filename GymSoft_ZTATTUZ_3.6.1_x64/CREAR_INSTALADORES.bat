@echo off
setlocal
cd /d "%~dp0"
call PREPARAR_PYTHON.bat
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -c "from product_config import VERSION; from release_gate import require_release_ready; require_release_ready('.', VERSION)"
if errorlevel 1 goto :pending_acceptance
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

:pending_acceptance
echo Esta carpeta contiene fuentes en desarrollo. Falta la aceptacion para crear instaladores finales.
echo Para abrir los programas y continuar las pruebas usa INICIAR_ADMINISTRADOR.bat o INICIAR_RECEPCION.bat.
echo Consulta ESTADO_ACTUAL.md y docs/INTEGRACIONES_Y_WINDOWS.md del respaldo.
pause
exit /b 1
