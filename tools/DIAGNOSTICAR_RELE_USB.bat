@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ATS_USB_SCRIPT=%~dp0diagnose_relay_usb.ps1"
if not exist "%ATS_USB_SCRIPT%" (
    echo Falta diagnose_relay_usb.ps1 junto a este archivo.
    pause
    exit /b 1
)
set "ATS_USB_POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
if defined PROCESSOR_ARCHITEW6432 if exist "%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe" set "ATS_USB_POWERSHELL=%SystemRoot%\Sysnative\WindowsPowerShell\v1.0\powershell.exe"
if not exist "%ATS_USB_POWERSHELL%" (
    echo No se encontro Windows PowerShell. No se cambiaron dispositivos.
    pause
    exit /b 1
)
echo Diagnostico de solo lectura. No requiere Python ni Administrador.
"%ATS_USB_POWERSHELL%" -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ATS_USB_SCRIPT%"
set "ATS_USB_RESULT=%ERRORLEVEL%"
if "%ATS_USB_RESULT%"=="2" echo Se guardo una coleccion parcial. Revise RESUMEN.txt.
if "%ATS_USB_RESULT%"=="1" echo No se completo la coleccion. Revise el aviso anterior.
pause
exit /b %ATS_USB_RESULT%
