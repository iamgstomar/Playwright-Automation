// ============================================================
//  Jenkinsfile — Puffin QA Automation Pipeline
//
//  Prerequisites on Jenkins agent:
//    - Python 3.10+
//    - Java 11+ (for Allure CLI)
//    - Allure Jenkins Plugin installed
//    - Git
//
//  Jenkins credentials needed:
//    - qa-config-yaml  : Secret File — your config/config.yaml
//    - qa-excel        : Secret File — your QA_Test_Cases.xlsx
// ============================================================

pipeline {

    agent any

    parameters {
        choice(
            name:        'MODULE',
            choices:     ['Departments', 'Login', 'ALL'],
            description: 'Which module to test'
        )
        string(
            name:        'LABEL',
            defaultValue: '',
            description: 'Build label shown in Allure Trend (e.g. Sprint 3). Leave blank for auto.'
        )
        booleanParam(
            name:         'REPORT_ONLY',
            defaultValue: false,
            description:  'Skip pytest — only regenerate Allure report from Excel'
        )
    }

    environment {
        ALLURE_RESULTS = 'allure-results'
        ALLURE_REPORT  = 'allure-report'
        VENV_DIR       = 'venv'
    }

    options {
        timestamps()
        timeout(time: 60, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    triggers {
        // Nightly run at 2am — comment out if not needed
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
                // Inject secret config and Excel from Jenkins credentials
                withCredentials([
                    file(credentialsId: 'qa-config-yaml', variable: 'CONFIG_FILE'),
                    file(credentialsId: 'qa-excel',       variable: 'EXCEL_FILE')
                ]) {
                    sh 'cp "$CONFIG_FILE" config/config.yaml'
                    sh 'cp "$EXCEL_FILE"  QA_Test_Cases.xlsx'
                }

                sh '''
                    python3 -m venv ${VENV_DIR}
                    . ${VENV_DIR}/bin/activate
                    pip install --quiet -r requirements.txt
                    playwright install chromium
                '''
            }
        }

        stage('Run Tests') {
            when {
                expression { return !params.REPORT_ONLY }
            }
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    if [ "${MODULE}" = "ALL" ]; then
                        pytest -v --alluredir=${ALLURE_RESULTS} --reruns 2 --reruns-delay 3
                    else
                        pytest -v --alluredir=${ALLURE_RESULTS} --reruns 2 --reruns-delay 3 \
                               -m "$(echo ${MODULE} | tr '[:upper:]' '[:lower:]')"
                    fi
                '''
            }
            post {
                always {
                    // Always write Excel results even if some tests failed
                    sh '. ${VENV_DIR}/bin/activate && python tools/excel_to_allure.py --all --label "${LABEL}"'
                }
            }
        }

        stage('Report Only') {
            when {
                expression { return params.REPORT_ONLY }
            }
            steps {
                sh '''
                    . ${VENV_DIR}/bin/activate
                    if [ "${MODULE}" = "ALL" ]; then
                        python tools/excel_to_allure.py --all --label "${LABEL}"
                    else
                        python tools/excel_to_allure.py --sheet "${MODULE}" --label "${LABEL}"
                    fi
                '''
            }
        }

        stage('Publish Report') {
            steps {
                // Allure Jenkins Plugin — renders report inside Jenkins
                allure([
                    includeProperties: true,
                    jdk:               '',
                    results:           [[path: "${ALLURE_RESULTS}"]],
                    report:            "${ALLURE_REPORT}",
                    reportBuildPolicy: 'ALWAYS'
                ])
            }
        }
    }

    post {
        failure {
            emailext(
                subject: "FAILED: Puffin QA — ${params.MODULE} — Build #${BUILD_NUMBER}",
                body:    """
                    Build #${BUILD_NUMBER} FAILED.
                    Module : ${params.MODULE}
                    Console: ${BUILD_URL}console
                    Report : ${BUILD_URL}allure/
                """,
                to: '$DEFAULT_RECIPIENTS'
            )
        }
        success {
            emailext(
                subject: "PASSED: Puffin QA — ${params.MODULE} — Build #${BUILD_NUMBER}",
                body:    """
                    Build #${BUILD_NUMBER} PASSED.
                    Module : ${params.MODULE}
                    Report : ${BUILD_URL}allure/
                """,
                to: '$DEFAULT_RECIPIENTS'
            )
        }
        always {
            cleanWs(patterns: [[pattern: 'venv/**', type: 'INCLUDE']])
        }
    }
}
