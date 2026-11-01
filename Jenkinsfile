
pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        choice(
            name: 'MODULE',
            choices: ['Departments', 'Login', 'ALL'],
            description: 'Select the test module to execute'
        )
    }

    environment {
        ALLURE_RESULTS = 'allure-results'
        ALLURE_REPORT  = 'allure-report'

        VENV_DIR       = 'venv'
        VENV_PYTHON    = 'venv\\Scripts\\python.exe'

        PYTHON_EXE     = 'C:\\Users\\Dell\\AppData\\Local\\Programs\\Python\\Python313\\python.exe'
    }

    stages {

        stage('Checkout Latest Code') {
            steps {
                echo 'Checking out latest source code...'

                checkout scm

                bat '''
                    echo Current Git commit:
                    git log -1 --oneline

                    echo Cleaning untracked workspace files...
                    git clean -fd

                    echo Git status:
                    git status
                '''
            }
        }

        stage('Setup Environment') {
            steps {
                echo 'Setting up Python environment...'

                withCredentials([
                    file(credentialsId: 'qa-config-yaml', variable: 'CONFIG_FILE'),
                    file(credentialsId: 'qa-excel', variable: 'EXCEL_FILE')
                ]) {
                    bat '''
                        if not exist "config" mkdir "config"

                        echo Copying configuration file...
                        copy /Y "%CONFIG_FILE%" "config\\config.yaml"
                        if errorlevel 1 exit /b 1

                        echo Copying QA test workbook...
                        copy /Y "%EXCEL_FILE%" "QA_Test_Cases.xlsx"
                        if errorlevel 1 exit /b 1
                    '''
                }

                bat '''
                    echo Checking system Python...
                    "%PYTHON_EXE%" --version
                    if errorlevel 1 exit /b 1

                    echo Checking existing virtual environment...

                    if exist "%VENV_DIR%" (
                        "%VENV_PYTHON%" -m pip --version >nul 2>&1
                        if errorlevel 1 (
                            echo Removing invalid virtual environment...
                            rmdir /S /Q "%VENV_DIR%"
                        )
                    )

                    if not exist "%VENV_PYTHON%" (
                        echo Creating Python virtual environment...
                        "%PYTHON_EXE%" -m venv "%VENV_DIR%"
                        if errorlevel 1 exit /b 1
                    )

                    echo Initializing pip...
                    "%VENV_PYTHON%" -m ensurepip --upgrade
                    if errorlevel 1 exit /b 1

                    echo Upgrading pip...
                    "%VENV_PYTHON%" -m pip install --upgrade pip
                    if errorlevel 1 exit /b 1

                    echo Installing dependencies...
                    "%VENV_PYTHON%" -m pip install -r requirements.txt
                    if errorlevel 1 exit /b 1

                    echo Installing Playwright Chromium...
                    "%VENV_PYTHON%" -m playwright install chromium
                    if errorlevel 1 exit /b 1

                    echo Verifying pytest...
                    "%VENV_PYTHON%" -m pytest --version
                    if errorlevel 1 exit /b 1

                    echo Python environment setup completed.
                '''
            }
        }

        stage('Run Selected Tests') {
            steps {
                script {
                    echo "Selected module: ${params.MODULE}"

                    bat '''
                        echo Preparing Allure results directory...

                        if not exist "%ALLURE_RESULTS%" mkdir "%ALLURE_RESULTS%"

                        powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path '%ALLURE_RESULTS%') { Get-ChildItem '%ALLURE_RESULTS%' -File | Remove-Item -Force; Get-ChildItem '%ALLURE_RESULTS%' -Directory | Where-Object { $_.Name -ne 'history' } | Remove-Item -Recurse -Force }"

                        if errorlevel 1 exit /b 1

                        echo ========================================
                        echo Selected module: %MODULE%
                        echo ========================================

                        if "%MODULE%"=="Departments" (
                            set "TEST_FILENAME=test_Departments.py"
                            goto RUN_SELECTED_TEST
                        )

                        if "%MODULE%"=="Login" (
                            set "TEST_FILENAME=test_login.py"
                            goto RUN_SELECTED_TEST
                        )

                        if "%MODULE%"=="ALL" (
                            echo Executing all pytest test files...
                            "%VENV_PYTHON%" -m pytest -v --alluredir="%ALLURE_RESULTS%" --reruns 2 --reruns-delay 3
                            exit /b %ERRORLEVEL%
                        )

                        echo Invalid module selected: %MODULE%
                        exit /b 1

                        :RUN_SELECTED_TEST

                        echo Searching for %TEST_FILENAME%...

                        set "TEST_FILE="

                        for /f "delims=" %%F in ('powershell -NoProfile -Command "Get-ChildItem -Path . -Filter '%TEST_FILENAME%' -File -Recurse | Where-Object { $_.FullName -notmatch '\\(venv|.git|.pytest_cache|__pycache__|allure-results|allure-report)\\' } | Select-Object -First 1 -ExpandProperty FullName"') do set "TEST_FILE=%%F"

                        if not defined TEST_FILE (
                            echo ERROR: Test file %TEST_FILENAME% was not found.
                            exit /b 1
                        )

                        echo Executing selected test file:
                        echo %TEST_FILE%

                        "%VENV_PYTHON%" -m pytest -v "%TEST_FILE%" --alluredir="%ALLURE_RESULTS%" --reruns 2 --reruns-delay 3

                        exit /b %ERRORLEVEL%
                    '''
                }
            }
        }

        stage('Publish Allure Report') {
            steps {
                echo 'Publishing Allure report from pytest execution results...'

                script {
                    if (!fileExists(env.ALLURE_RESULTS)) {
                        error 'Allure results directory was not created.'
                    }

                    allure([
                        includeProperties: true,
                        jdk: '',
                        results: [[path: "${ALLURE_RESULTS}"]],
                        report: "${ALLURE_REPORT}",
                        reportBuildPolicy: 'ALWAYS'
                    ])
                }
            }
        }
    }

    post {

        success {
            echo 'QA Automation completed successfully.'
        }

        unstable {
            echo 'QA Automation completed with test failures.'
        }

        failure {
            echo 'QA Automation pipeline failed. Please check the Jenkins console output.'
        }

        always {
            echo 'Cleaning Python virtual environment...'

            bat '''
                if exist "%VENV_DIR%" (
                    rmdir /S /Q "%VENV_DIR%"
                )
            '''

            echo 'Cleanup completed.'
        }
    }
}