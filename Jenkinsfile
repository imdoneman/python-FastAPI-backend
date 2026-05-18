pipeline {
    agent any

    environment {
        // Define standard workspace variables if needed
        APP_NAME = "tea-house-api"
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/imdoneman/python-FastAPI-backend.git'
            }
        }

        stage('Build, Test & Deploy Stack') {
            steps {
                echo 'Starting Container Compilation and Running Embedded Pytest Suite...'
                
                // Trigger the multi-stage build. 
                // Jenkins will fail right here if any of your pytests fail!
                sh "docker compose down"
                sh "docker compose up -d --build"
                
                echo 'Stack successfully verified and running in detached mode!'
            }
        }

        stage('Verify Runtime Sanity') {
            steps {
                echo 'Executing endpoint verification checks...'
                script {
                    // Give the application a few seconds to boot up completely
                    sh "sleep 5"
                    
                    // Hit the pulse healthcheck route to confirm life signs
                    def response = sh(script: "curl -s http://localhost:8000/pulse", returnStdout: true).trim()
                    echo "Healthcheck Response: ${response}"
                    
                    if (!response.contains('"status":"online"')) {
                        error("Sanity Check Failed: Application is unreachable or offline.")
                    }
                }
            }
        }
    }

    post {
        success {
            echo 'Pipeline completed flawlessly. Production stack updated successfully!'
        }
        failure {
            echo 'Pipeline execution encountered errors. Check the Docker build logs above to inspect failed test cases.'
        }
    }
}