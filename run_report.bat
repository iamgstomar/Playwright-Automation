@echo off
:: ============================================================
::  run_report.bat — One-click Allure report pipeline
::  Usage:
::    run_report.bat                        (Departments only)
::    run_report.bat --sheet Login
::    run_report.bat --all
::    run_report.bat --all --label "Sprint 3"
:: ============================================================

setlocal
set ROOT=%~dp0
set ALLURE=%ROOT%allure\allure-2.30.0\bin\allure.bat
set ARGS=%*

:: Default sheet if no args given
if "%ARGS%"=="" set ARGS=--sheet Departments

echo.
echo [1/4] Generating Allure results from Excel...
python "%ROOT%tools\excel_to_allure.py" %ARGS%
if errorlevel 1 ( echo ERROR: excel_to_allure.py failed & pause & exit /b 1 )

echo.
echo [2/4] Generating Allure report...
cmd /c "%ALLURE%" generate allure-results --clean -o allure-report
if errorlevel 1 ( echo ERROR: allure generate failed & pause & exit /b 1 )

echo.
echo [3/4] Applying dark theme...
python "%ROOT%tools\apply_dark_theme.py"
if errorlevel 1 ( echo ERROR: apply_dark_theme.py failed & pause & exit /b 1 )

echo.
echo [4/4] Opening report at http://localhost:5050 ...
echo       Press Ctrl+C in this window to stop the server.
echo.
cmd /c "%ALLURE%" open allure-report --port 5050
