@echo off
rem Preparador compartido. No requiere el comando py si Python ya esta instalado.
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto :validate
where py >nul 2>nul
if not errorlevel 1 (
  py -3.13-32 -m venv .venv
  if exist ".venv\Scripts\python.exe" goto :validate
)
for %%P in ("C:\Python313-32\python.exe" "C:\Python313\python.exe" "%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe" "%ProgramFiles%\Python313\python.exe") do (
  if exist "%%~P" (
    "%%~P" -c "import sys,struct;sys.exit(0 if sys.version_info[:2]==(3,13) and struct.calcsize('P')==4 else 1)"
    if not errorlevel 1 "%%~P" -m venv .venv
    if exist ".venv\Scripts\python.exe" goto :validate
  )
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys,struct;sys.exit(0 if sys.version_info[:2]==(3,13) and struct.calcsize('P')==4 else 1)"
  if not errorlevel 1 python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
  echo No se encontro Python 3.13 de 32 bits. Instalalo y vuelve a ejecutar este archivo.
  exit /b 1
)
:validate
".venv\Scripts\python.exe" -c "import sys,struct;sys.exit(0 if sys.version_info[:2]==(3,13) and struct.calcsize('P')==4 else 1)"
if errorlevel 1 (
  echo El entorno actual no usa Python 3.13 de 32 bits. Extrae el paquete en una carpeta nueva.
  exit /b 1
)
exit /b 0
