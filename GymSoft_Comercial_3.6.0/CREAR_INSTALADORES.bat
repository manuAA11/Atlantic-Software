@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
call PREPARAR_PYTHON.bat
if errorlevel 1 goto :error
set "ATLANTIC_BUILD_MODE=FINAL"
".venv\Scripts\python.exe" -c "from product_config import VERSION; from release_gate import require_release_ready; require_release_ready('.', VERSION)"
if errorlevel 1 set "ATLANTIC_BUILD_MODE=PRUEBAS_PARA_CONFIGURAR"
if "%ATLANTIC_BUILD_MODE%"=="PRUEBAS_PARA_CONFIGURAR" (
  echo La aceptacion final sigue pendiente. Se crearan instaladores para configurar y probar.
  echo Se ejecutaran todas las pruebas locales. Si alguna falla, no se publicara una nueva entrega.
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip check
if errorlevel 1 goto :error
call PREPARAR_PRUEBAS.bat
if errorlevel 1 goto :error
if "%ATLANTIC_BUILD_MODE%"=="FINAL" goto :final
if not exist "..\tools\windows_packaging_qa.py" goto :missing_qa
".venv\Scripts\python.exe" "..\tools\windows_packaging_qa.py" --installers --para-configurar
if errorlevel 1 goto :error
echo Instaladores NO FINAL para configurar y probar: salida\PRUEBAS_PARA_CONFIGURAR.
echo Consulta LEER_PRIMERO.txt en la carpeta de esta ejecucion.
if not "%GYMSOFT_BUILD_NONINTERACTIVE%"=="1" pause
exit /b 0

:final
".venv\Scripts\python.exe" build_windows.py
if errorlevel 1 goto :error
echo Instalador final de clientes y panel privado del propietario generados en salida.
if not "%GYMSOFT_BUILD_NONINTERACTIVE%"=="1" pause
exit /b 0

:missing_qa
echo Falta tools\windows_packaging_qa.py. Extrae el paquete completo en una carpeta nueva.
goto :error

:error
echo La compilacion no termino. Revisa el error anterior; no entregues archivos incompletos.
if not "%GYMSOFT_BUILD_NONINTERACTIVE%"=="1" pause
exit /b 1
