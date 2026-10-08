@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ejecuta primero CREAR_INSTALADORES.bat para preparar Python.
  pause
  exit /b 1
)
echo Deja las ventanas de prueba visibles y el escritorio desbloqueado hasta terminar.
".venv\Scripts\python.exe" tests\windows_ui_smoke.py
if errorlevel 1 (
  echo La prueba grafica fallo. Copia el error de esta ventana.
  pause
  exit /b 1
)
for %%T in (responsive_ui_smoke biometric_ui_smoke ticket_ui_smoke performance_ui_smoke popdown_ui_smoke layout_modes_ui_smoke) do (
  ".venv\Scripts\python.exe" tests\%%T.py
  if errorlevel 1 (
    echo Fallo la prueba %%T. Copia el error de esta ventana.
    pause
    exit /b 1
  )
)
echo Pruebas completadas sin usar cuentas ni modificar datos.
pause
