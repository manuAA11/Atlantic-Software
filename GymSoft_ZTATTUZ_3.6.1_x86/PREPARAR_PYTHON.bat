@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
rem Reuse a valid environment; check version, architecture and actual venv prefix.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "%~dp0preparar_entorno.py" --check-environment --bits 32 >nul 2>nul
  if not errorlevel 1 exit /b 0
  echo El .venv actual es incompatible. Buscando Python 3.14 o 3.13 de 32 bits...
)
call :try_python py -3.14-32
if errorlevel 2 goto :failed
if not errorlevel 1 exit /b 0
call :try_python py -3.14
if errorlevel 2 goto :failed
if not errorlevel 1 exit /b 0
call :try_python py -3.13-32
if errorlevel 2 goto :failed
if not errorlevel 1 exit /b 0
call :try_python py -3.13
if errorlevel 2 goto :failed
if not errorlevel 1 exit /b 0
call :try_python py
if errorlevel 2 goto :failed
if not errorlevel 1 exit /b 0
for %%P in ("C:\Python314-32\python.exe" "C:\Python314\python.exe" "%LOCALAPPDATA%\Programs\Python\Python314-32\python.exe" "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" "%LOCALAPPDATA%\Python\pythoncore-3.14-32\python.exe" "%ProgramFiles%\Python314\python.exe" "%ProgramFiles(x86)%\Python314\python.exe") do (
  if exist "%%~P" (
    call :try_python "%%~P"
    if errorlevel 2 goto :failed
    if not errorlevel 1 exit /b 0
  )
)
for %%P in ("C:\Python313-32\python.exe" "C:\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe" "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" "%LOCALAPPDATA%\Python\pythoncore-3.13-32\python.exe" "%ProgramFiles%\Python313\python.exe" "%ProgramFiles(x86)%\Python313\python.exe") do (
  if exist "%%~P" (
    call :try_python "%%~P"
    if errorlevel 2 goto :failed
    if not errorlevel 1 exit /b 0
  )
)
call :try_python python
if errorlevel 2 goto :failed
if not errorlevel 1 exit /b 0
echo No se encontro CPython 3.13 o 3.14 de 32 bits (edicion estandar con GIL).
echo Python 3.14 es compatible. Revisa py -0p y la arquitectura de esta carpeta.
echo Descarga oficial: https://www.python.org/downloads/windows/
exit /b 1

:try_python
%* "%~dp0preparar_entorno.py" --check --bits 32 >nul 2>nul
if errorlevel 1 exit /b 1
%* "%~dp0preparar_entorno.py" --bits 32
if errorlevel 1 exit /b 2
exit /b 0

:failed
echo No se pudo preparar .venv. Cierra las aplicaciones que lo usan y revisa el mensaje anterior.
echo El entorno anterior se conserva; no se generaron instaladores.
exit /b 1
