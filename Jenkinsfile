// ============================================================================
// MODULE REGISTRY
// To add a new module in the future:
//   1. Add one line here          ->  'ModuleName': 'test_file_name.py'
//   2. Add the same name to the MODULE parameter 'value' list below
// Nothing else in this pipeline needs to change.
// ============================================================================
def MODULE_TESTS = [
    'Departments': 'test_Departments.py',
    'Login'      : 'test_login.py'
]

pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    parameters {
        // Single MODULE field with multi-select (requires the "Extended Choice Parameter" plugin).
        // Keep 'value' in sync with MODULE_TESTS above (ALL must stay last).
        extendedChoice(
            name: 'MODULE',
            type: 'PT_MULTI_SELECT',
            value: 'Departments,Login,ALL',
            defaultValue: 'Departments',
            multiSelectDelimiter: ',',
            visibleItemCount: 5,
            description: 'Select the test module(s) to execute (Ctrl+click to select more than one)'
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

                    echo Installing project dependencies...
                    "%VENV_PYTHON%" -m pip install -r requirements.txt
                    if errorlevel 1 exit /b 1

                    echo Installing Playwright Chromium...
                    "%VENV_PYTHON%" -m playwright install chromium
                    if errorlevel 1 exit /b 1

                    echo Verifying pytest...
                    "%VENV_PYTHON%" -m pytest --version
                    if errorlevel 1 exit /b 1

                    echo Python environment setup completed successfully.
                '''
            }
        }

        stage('Run Selected Tests') {
            steps {
                echo "Selected module: ${params.MODULE}"

                // Prepare Allure results directory (unchanged)
                bat '''
                    echo Preparing Allure results directory...

                    if not exist "%ALLURE_RESULTS%" mkdir "%ALLURE_RESULTS%"

                    powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Test-Path '%ALLURE_RESULTS%') { Get-ChildItem '%ALLURE_RESULTS%' -File | Remove-Item -Force; Get-ChildItem '%ALLURE_RESULTS%' -Directory | Where-Object { $_.Name -ne 'history' } | Remove-Item -Recurse -Force }"

                    if errorlevel 1 exit /b 1

                    echo ========================================
                    echo Selected module: %MODULE%
                    echo ========================================
                '''

                script {
                    // Parse the (possibly comma-separated) selection
                    def selected = (params.MODULE ?: '')
                        .split(',')
                        .collect { it.trim() }
                        .findAll { it }
                        .unique()

                    if (selected.isEmpty()) {
                        error 'No module selected. Please select at least one module or ALL.'
                    }

                    def pytestTargets = ''   // empty = run all pytest test files

                    if (selected.contains('ALL')) {
                        echo 'ALL selected - executing all pytest test files...'
                    } else {
                        // Validate every selected module against the registry
                        def invalid = selected.findAll { !MODULE_TESTS.containsKey(it) }
                        if (!invalid.isEmpty()) {
                            error "Invalid module(s) selected: ${invalid.join(', ')}. " +
                                  "Valid modules: ${MODULE_TESTS.keySet().join(', ')}, ALL"
                        }

                        // Locate each test file anywhere in the workspace (same behaviour as before)
                        def resolved = []
                        for (m in selected) {
                            def fileName = MODULE_TESTS[m]
                            echo "Searching for ${fileName}..."

                            def found = bat(
                                script: "@echo off\ndir /s /b \"${fileName}\" 2>nul\nexit /b 0",
                                returnStdout: true
                            ).trim()

                            if (!found) {
                                error "${fileName} was not found."
                            }

                            def firstMatch = found.readLines()[0].trim()
                            echo "Module ${m} -> ${firstMatch}"
                            resolved << "\"${firstMatch}\""
                        }

                        pytestTargets = resolved.join(' ')
                    }

                    echo '========================================'
                    echo "Modules to run : ${selected.join(', ')}"
                    echo "Pytest targets : ${pytestTargets ?: '(all tests)'}"
                    echo '========================================'

                    // Single pytest run => one combined Allure report
                    bat """
                        "%VENV_PYTHON%" -m pytest -v ${pytestTargets} --alluredir="%ALLURE_RESULTS%" --reruns 2 --reruns-delay 3

                        exit /b %ERRORLEVEL%
                    """
                }
            }
        }

        stage('Publish Allure Report') {
            steps {
                echo 'Publishing Allure report from pytest results...'

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
            echo 'QA Automation completed successfully.'
        }

        unstable {
            echo 'QA Automation completed with test failures.'
        }

        failure {
            echo 'QA Automation pipeline failed. Check Jenkins console output.'
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