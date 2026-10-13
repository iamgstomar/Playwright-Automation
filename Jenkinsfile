
pipeline {

    agent any

    parameters {
        choice(
            name: 'MODULE',
            choices: ['Departments', 'Login', 'ALL'],
            description: 'Which module to test'
        )

        string(
            name: 'LABEL',
            defaultValue: '',
            description: 'Build label shown in Allure Trend. Leave blank for auto.'
        )

        booleanParam(
            name: 'REPORT_ONLY',
            defaultValue: false,
            description: 'Skip pytest and regenerate report from Excel'
        )
    }

    environment {
        ALLURE_RESULTS = 'allure-results'
        ALLURE_REPORT  = 'allure-report'
        VENV_DIR       = 'venv'
        PYTHON_EXE     = 'C:\\Users\\Dell\\AppData\\Local\\Programs\\Python\\Python313\\python.exe'
    }

    options {
        timestamps()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    triggers {
        // Runs nightly at 2 AM according to Jenkins timezone
        cron('0 2 * * *')
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Setup') {
            steps {
                echo 'Setting up Python environment and QA files'

                withCredentials([
                    file(
                        credentialsId: 'qa-config-yaml',
                        variable: 'CONFIG_FILE'
                    ),
                    file(
                        credentialsId: 'qa-excel',
                        variable: 'EXCEL_FILE'
                    )
                ]) {
                    bat '''
                        if not exist "config" mkdir "config"

                        copy /Y "%CONFIG_FILE%" "config\\config.yaml"
                        if errorlevel 1 exit /b 1

                        copy /Y "%EXCEL_FILE%" "QA_Test_Cases.xlsx"
                        if errorlevel 1 exit /b 1
                    '''
                }

                bat '''
                    echo Checking Python installation...

                    if not exist "%PYTHON_EXE%" (
                        echo ERROR: Python executable not found.
                        echo Expected path: %PYTHON_EXE%
                        exit /b 1
                    )

                    "%PYTHON_EXE%" --version
                    if errorlevel 1 exit /b 1

                    echo Checking virtual environment...

                    if not exist "%VENV_DIR%\\Scripts\\python.exe" (
                        "%PYTHON_EXE%" -m venv "%VENV_DIR%"
                        if errorlevel 1 exit /b 1
                    )

                    "%VENV_DIR%\\Scripts\\python.exe" --version
                    if errorlevel 1 exit /b 1

                    echo Upgrading pip...

                    "%VENV_DIR%\\Scripts\\python.exe" -m pip install --upgrade pip
                    if errorlevel 1 exit /b 1

                    echo Installing project dependencies...

                    "%VENV_DIR%\\Scripts\\python.exe" -m pip install --quiet -r requirements.txt
                    if errorlevel 1 exit /b 1

                    echo Installing Playwright Chromium...

                    "%VENV_DIR%\\Scripts\\python.exe" -m playwright install chromium
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
                echo 'Running Playwright automation tests'

                bat '''
                    if not exist "%ALLURE_RESULTS%" (
                        mkdir "%ALLURE_RESULTS%"
                    )

                    if /I "%MODULE%"=="ALL" (
                        "%VENV_DIR%\\Scripts\\python.exe" -m pytest -v --alluredir="%ALLURE_RESULTS%" --reruns 2 --reruns-delay 3
                        exit /b %errorlevel%
                    ) else (
                        "%VENV_DIR%\\Scripts\\python.exe" -c "print('Selected module: %MODULE%')"
                        if errorlevel 1 exit /b 1

                        "%VENV_DIR%\\Scripts\\python.exe" -m pytest -v --alluredir="%ALLURE_RESULTS%" --reruns 2 --reruns-delay 3 -m "%MODULE%"
                        exit /b %errorlevel%
                    )
                '''
            }

            post {
                always {
                    echo 'Updating Excel test results'

                    bat '''
                        if exist "%VENV_DIR%\\Scripts\\python.exe" (
                            "%VENV_DIR%\\Scripts\\python.exe" tools\\excel_to_allure.py --all --label "%LABEL%"
                        ) else (
                            echo Python virtual environment not found. Excel update skipped.
                        )
                    '''
                }
            }
        }

        stage('Report Only') {
            when {
                expression {
                    return params.REPORT_ONLY
                }
            }

            steps {
                echo 'Generating report without executing tests'

                bat '''
                    if not exist "%VENV_DIR%\\Scripts\\python.exe" (
                        echo ERROR: Python virtual environment not found.
                        exit /b 1
                    )

                    if /I "%MODULE%"=="ALL" (
                        "%VENV_DIR%\\Scripts\\python.exe" tools\\excel_to_allure.py --all --label "%LABEL%"
                    ) else (
                        "%VENV_DIR%\\Scripts\\python.exe" tools\\excel_to_allure.py --sheet "%MODULE%" --label "%LABEL%"
                    )

                    if errorlevel 1 exit /b 1
                '''
            }
        }

        stage('Publish Report') {
            steps {
                echo 'Publishing Allure report in Jenkins'

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

    post {
        failure {
            emailext(
                subject: "FAILED: Puffin QA - ${params.MODULE} - Build #${BUILD_NUMBER}",
                body: """
                    Build #${BUILD_NUMBER} FAILED.

                    Module: ${params.MODULE}

                    Console Output:
                    ${BUILD_URL}console

                    Allure Report:
                    ${BUILD_URL}allure/
                """,
                to: '$DEFAULT_RECIPIENTS'
            )
        }

        success {
            emailext(
                subject: "PASSED: Puffin QA - ${params.MODULE} - Build #${BUILD_NUMBER}",
                body: """
                    Build #${BUILD_NUMBER} PASSED.

                    Module: ${params.MODULE}

                    Allure Report:
                    ${BUILD_URL}allure/
                """,
                to: '$DEFAULT_RECIPIENTS'
            )
        }

        always {
            cleanWs(
                patterns: [
                    [pattern: 'venv/**', type: 'INCLUDE']
                ]
            )
        }
    }
}
