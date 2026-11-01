
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
        skipDefaultCheckout(true)
    }

    stages {

        stage('Checkout Latest Code') {
            steps {
                echo 'Checking out the configured GitHub branch...'

                checkout scm

                echo 'Removing obsolete untracked files from Jenkins workspace...'

                bat '''
                    git clean -fd
                    if errorlevel 1 exit /b 1

                    echo ---- Current Git status ----
                    git status --short

                    echo ---- Latest Git commit ----
                    git log -1 --oneline
                '''
            }
        }

        stage('Setup') {
            steps {
                echo 'Setting up Python environment and QA files'

                withCredentials([
                    file(credentialsId: 'qa-config-yaml', variable: 'CONFIG_FILE'),
                    file(credentialsId: 'qa-excel', variable: 'EXCEL_FILE')
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
                    echo ---- Paths used by this run ----
                    findstr /I /C:"excel_path" /C:"screenshot_dir" "config\\config.yaml"
                    exit /b 0
                '''

                bat '''
                    echo Checking Python installation...

                    if not exist "%PYTHON_EXE%" (
                        echo ERROR: Python executable not found: %PYTHON_EXE%
                        exit /b 1
                    )

                    "%PYTHON_EXE%" --version
                    if errorlevel 1 exit /b 1

                    echo Recreating Python virtual environment...

                    if exist "%VENV_DIR%" (
                        rmdir /S /Q "%VENV_DIR%"
                        if errorlevel 1 exit /b 1
                    )

                    "%PYTHON_EXE%" -m venv "%VENV_DIR%"
                    if errorlevel 1 exit /b 1

                    echo Repairing pip installation...

                    "%VENV_DIR%\\Scripts\\python.exe" -m ensurepip --upgrade
                    if errorlevel 1 exit /b 1

                    echo Verifying pip...

                    "%VENV_DIR%\\Scripts\\python.exe" -m pip --version
                    if errorlevel 1 exit /b 1

                    echo Upgrading pip...

                    "%VENV_DIR%\\Scripts\\python.exe" -m pip install --upgrade pip
                    if errorlevel 1 exit /b 1

                    echo Installing project dependencies...

                    "%VENV_DIR%\\Scripts\\python.exe" -m pip install -r requirements.txt
                    if errorlevel 1 exit /b 1

                    echo Verifying pytest installation...

                    "%VENV_DIR%\\Scripts\\python.exe" -m pytest --version
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
                expression { return !params.REPORT_ONLY }
            }

            steps {
                echo "Running tests for module: ${params.MODULE}"

                // Clear previous Allure result files for this execution.
                bat '''
                    if not exist "%ALLURE_RESULTS%" mkdir "%ALLURE_RESULTS%"
                    del /Q "%ALLURE_RESULTS%\\*" 2>nul
                    exit /b 0
                '''

                catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                    bat '''
                        if /I "%MODULE%"=="ALL" (
                            "%VENV_DIR%\\Scripts\\python.exe" -m pytest -v --alluredir="%ALLURE_RESULTS%"
                            if errorlevel 1 exit /b 1
                        ) else if /I "%MODULE%"=="Departments" (
                            "%VENV_DIR%\\Scripts\\python.exe" -m pytest -v --alluredir="%ALLURE_RESULTS%" -m "departments"
                            if errorlevel 1 exit /b 1
                        ) else if /I "%MODULE%"=="Login" (
                            "%VENV_DIR%\\Scripts\\python.exe" -m pytest -v --alluredir="%ALLURE_RESULTS%" -m "login"
                            if errorlevel 1 exit /b 1
                        ) else (
                            echo ERROR: Unsupported module "%MODULE%"
                            exit /b 1
                        )
                    '''
                }

                echo 'Updating Excel and generating Allure test results'

                script {
                    def sheetArg = (params.MODULE == 'ALL')
                        ? '--all'
                        : "--sheet \"${params.MODULE}\""

                    bat """
                        if not exist "%VENV_DIR%\\Scripts\\python.exe" (
                            echo ERROR: Python virtual environment not found.
                            exit /b 1
                        )

                        "%VENV_DIR%\\Scripts\\python.exe" tools\\excel_to_allure.py ${sheetArg} --label "%LABEL%"
                        if errorlevel 1 exit /b 1
                    """
                }
            }
        }

        stage('Report Only') {
            when {
                expression { return params.REPORT_ONLY }
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
                        if errorlevel 1 exit /b 1
                    ) else if /I "%MODULE%"=="Departments" (
                        "%VENV_DIR%\\Scripts\\python.exe" tools\\excel_to_allure.py --sheet "Departments" --label "%LABEL%"
                        if errorlevel 1 exit /b 1
                    ) else if /I "%MODULE%"=="Login" (
                        "%VENV_DIR%\\Scripts\\python.exe" tools\\excel_to_allure.py --sheet "Login" --label "%LABEL%"
                        if errorlevel 1 exit /b 1
                    ) else (
                        echo ERROR: Unsupported module "%MODULE%"
                        exit /b 1
                    )
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