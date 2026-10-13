@echo off
:: ============================================================
::  run_tests.bat — Run pytest and generate Allure report
::  Usage:
::    run_tests.bat                         (all tests)
::    run_tests.bat -k "departments"        (filter by keyword)
::    run_tests.bat tests/test_Departments.py
:: ============================================================

setlocal
set ROOT=%~dp0
set ALLURE=%ROOT%allure\allure-2.30.0\bin\allure.bat
set ARGS=%*

echo.
echo [1/4] Running tests...
call "%ROOT%venv\Scripts\activate.bat" 2>nul
pytest -v --alluredir=allure-results %ARGS%
set EXIT_CODE=%errorlevel%

echo.
echo [2/4] Generating Allure report...
cmd /c "%ALLURE%" generate allure-results --clean -o allure-report

echo.
echo [3/4] Applying dark theme...
python "%ROOT%tools\apply_dark_theme.py"

echo.
echo [4/4] Opening report at http://localhost:5050 ...
echo       Press Ctrl+C to stop the server.
echo.
cmd /c "%ALLURE%" open allure-report --port 5050

exit /b %EXIT_CODE%
