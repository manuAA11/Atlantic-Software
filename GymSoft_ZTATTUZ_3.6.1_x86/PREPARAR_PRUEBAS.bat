@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 goto :missing
where npm >nul 2>nul
if errorlevel 1 goto :missing
if exist "node_modules\@electric-sql\pglite\package.json" exit /b 0
call npm ci --ignore-scripts --no-audit --no-fund
exit /b %errorlevel%
:missing
echo La simulacion requiere Node.js LTS en el equipo donde compilas.
echo Instala Node.js desde https://nodejs.org y vuelve a abrir el archivo .bat.
echo Los computadores de los gimnasios no necesitan Node.js ni Python.
exit /b 1
