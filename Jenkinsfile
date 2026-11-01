
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

        string(
            name: 'LABEL',
            defaultValue: '',
            description: 'Optional label for Allure reporting'
        )

        booleanParam(
            name: 'REPORT_ONLY',
            defaultValue: false,
            description: 'Generate Allure report from Excel without executing tests'
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
                echo 'Checking out the latest source code...'

                checkout scm

                bat '''
                    echo Current Git commit:
                    git log -1 --oneline

                    echo Cleaning untracked workspace files...
                    git clean -fd

                    echo Git working tree status:
                    git status
                '''
            }
        }

        stage('Setup Environment') {
            steps {
                echo 'Setting up Python environment and project dependencies...'

                withCredentials([
                    file(credentialsId: 'qa-config-yaml', variable: 'CONFIG_FILE'),
                    file(credentialsId: 'qa-excel', variable: 'EXCEL_FILE')
                ]) {
                    bat '''
                        if not exist "config" mkdir "config"

                        echo Copying application configuration...
                        copy /Y "%CONFIG_FILE%" "config\\config.yaml"
                        if errorlevel 1 exit /b 1

                        echo Copying QA test cases workbook...
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
                            echo Existing virtual environment is invalid.
                            echo Recreating virtual environment...
                            rmdir /S /Q "%VENV_DIR%"
                        )
                    )

                    if not exist "%VENV_PYTHON%" (
                        echo Creating Python virtual environment...
                        "%PYTHON_EXE%" -m venv "%VENV_DIR%"
                        if errorlevel 1 exit /b 1
                    )

                    echo Checking virtual environment Python...
                    "%VENV_PYTHON%" --version
                    if errorlevel 1 exit /b 1

                    echo Initializing pip...
                    "%VENV_PYTHON%" -m ensurepip --upgrade
                    if errorlevel 1 exit /b 1

                    echo Upgrading pip...
                    "%VENV_PYTHON%" -m pip install --upgrade pip
                    if errorlevel 1 exit /b 1

                    echo Installing project dependencies...
                    "%VENV_PYTHON%" -m pip install -r requirements.txt
                    if errorlevel 1 exit /b 1

                    echo Installing Playwright Chromium...
                    "%VENV_PYTHON%" -m playwright install chromium
                    if errorlevel 1 exit /b 1

                    echo Verifying pytest installation...
                    "%VENV_PYTHON%" -m pytest --version
                    if errorlevel 1 exit /b 1

                    echo Python environment setup completed successfully.
                '''
            }
        }

        stage('Run Tests') {
            when {
                expression {
                    return !params.REPORT_ONLY
                }
            }

            steps {
                echo "Executing ${params.MODULE} test cases..."

                catchError(
                    buildResult: 'UNSTABLE',
                    stageResult: 'FAILURE'
                ) {
                    bat '''
                        if not exist "%ALLURE_RESULTS%" mkdir "%ALLURE_RESULTS%"

                        echo Removing previous Allure execution results...

                        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
                        "$p = '%ALLURE_RESULTS%'; ^
                         if (Test-Path $p) { ^
                             Get-ChildItem -Path $p -File | Remove-Item -Force; ^
                             Get-ChildItem -Path $p -Directory | Where-Object { $_.Name -ne 'history' } | Remove-Item -Recurse -Force ^
                         }"

                        if errorlevel 1 exit /b 1

                        if "%MODULE%"=="ALL" (
                            "%VENV_PYTHON%" -m pytest -v --alluredir="%ALLURE_RESULTS%" --reruns 2 --reruns-delay 3
                        ) else if "%MODULE%"=="Departments" (
                            "%VENV_PYTHON%" -m pytest -v -m "departments" --alluredir="%ALLURE_RESULTS%" --reruns 2 --reruns-delay 3
                        ) else if "%MODULE%"=="Login" (
                            "%VENV_PYTHON%" -m pytest -v -m "login" --alluredir="%ALLURE_RESULTS%" --reruns 2 --reruns-delay 3
                        ) else (
                            echo Invalid MODULE parameter: %MODULE%
                            exit /b 1
                        )

                        if errorlevel 1 exit /b 1
                    '''
                }
            }
        }

        stage('Generate Allure Results from Excel') {
            when {
                expression {
                    return params.REPORT_ONLY
                }
            }

            steps {
                echo "Generating Allure results from Excel for ${params.MODULE}..."

                bat '''
                    if not exist "%ALLURE_RESULTS%" mkdir "%ALLURE_RESULTS%"

                    if "%MODULE%"=="ALL" (
                        "%VENV_PYTHON%" tools\\excel_to_allure.py --all --label "%LABEL%"
                    ) else (
                        "%VENV_PYTHON%" tools\\excel_to_allure.py --sheet "%MODULE%" --label "%LABEL%"
                    )

                    if errorlevel 1 exit /b 1
                '''
            }
        }

        stage('Publish Allure Report') {
            steps {
                echo 'Publishing Allure report...'

                script {
                    if (!fileExists(env.ALLURE_RESULTS)) {
                        error 'Allure results directory does not exist.'
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
            echo 'Puffin QA Automation completed successfully.'

            emailext(
                to: '$DEFAULT_RECIPIENTS',
                subject: "SUCCESS: ${env.JOB_NAME} - Build #${env.BUILD_NUMBER}",
                body: """
Hello Team,

Puffin QA Automation execution completed successfully.

Build Details:
Job: ${env.JOB_NAME}
Build Number: ${env.BUILD_NUMBER}
Selected Module: ${params.MODULE}
Report Only: ${params.REPORT_ONLY}
Build Status: PASSED

Allure Report:
${env.BUILD_URL}allure/

Build URL:
${env.BUILD_URL}

Regards,
QA Automation
"""
            )
        }

        failure {
            echo 'Puffin QA Automation failed.'

            emailext(
                to: '$DEFAULT_RECIPIENTS',
                subject: "FAILED: ${env.JOB_NAME} - Build #${env.BUILD_NUMBER}",
                body: """
Hello Team,

Puffin QA Automation execution failed.

Build Details:
Job: ${env.JOB_NAME}
Build Number: ${env.BUILD_NUMBER}
Selected Module: ${params.MODULE}
Report Only: ${params.REPORT_ONLY}
Build Status: FAILED

Please review the Jenkins console output and Allure report.

Console Output:
${env.BUILD_URL}console

Allure Report:
${env.BUILD_URL}allure/

Build URL:
${env.BUILD_URL}

Regards,
QA Automation
"""
            )
        }

        unstable {
            echo 'Puffin QA Automation completed with test failures or unstable results.'
        }

        always {
            echo 'Performing Jenkins workspace cleanup...'

            bat '''
                if exist "%VENV_DIR%" (
                    echo Removing Python virtual environment...
                    rmdir /S /Q "%VENV_DIR%"
                )

                echo Virtual environment cleanup completed.
            '''
        }
    }
}