pipeline {
    agent any
    
    stages {
        stage('Checkout') {
            steps {
                git branch: 'main',
                    url: 'https://github.com/imdoneman/python-FastAPI-backend.git'
            }
        }
        
        stage('Build & Test') {
            steps {
                echo 'Starting Multi-Stage Docker Build...'
                // This runs your Alpine builder, runs pytest, and creates the runner image
                sh 'docker build -t tea-house-api:latest .'
            }
        }
        
        stage('Deploy Local') {
            steps {
                echo 'Deploying to Test Environment...'
                // Remove old container if it exists and start the new one
                sh 'docker rm -f tea-house-container || true'
                sh 'docker run -d -p 8000:8000 --name tea-house-container tea-house-api:latest'
            }
        }
    }
}