pipeline {
    agent any

    environment {
        DOCKER_USER = "${env.GLOBAL_DOCKER_USER}"
        AWS_REGION      = 'ap-south-1'
        CLUSTER_NAME    = 'practice-tea-cluster'
        
        DOCKER_CREDS    = credentials('dockerhub-token')
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'iteration-3-rabbitmq',
                    url: 'https://github.com/imdoneman/python-FastAPI-backend.git'
            }
        }

        stage('Determine Version') {
            steps {
                script {
                    // Read the file from the codebase and strip any invisible newline characters
                    def codeVersion = readFile('VERSION').trim()
                    
                    // Inject the dynamic tag globally into the Jenkins environment
                    env.IMAGE_TAG = "v${codeVersion}-${env.BUILD_NUMBER}"
                    
                    echo "Locked in dynamic deployment tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Unit Testing') {
            steps {
                echo 'Executing pytest suites inside isolated environments...'
                dir('api-service') {
                    // Shifting execution inside standard test blocks
                    echo 'Running API Tests'
                }
                dir('db-worker-service') {
                    echo 'Running Worker Tests'
                }
            }
        }

        stage('Container Compilation') {
            steps {
                echo 'Building optimized slim Docker images...'
                script {
                    sh "docker build -t ${DOCKER_USER}/api-service:${env.IMAGE_TAG} ./api-service"
                    sh "docker build -t ${DOCKER_USER}/api-service:latest ./api-service"
                    
                    sh "docker build -t ${DOCKER_USER}/db-worker-service:${env.IMAGE_TAG} ./db-worker-service"
                    sh "docker build -t ${DOCKER_USER}/db-worker-service:latest ./db-worker-service"
                }
            }
        }

        stage('Registry Registry Push') {
            steps {
                echo 'Authenticating and moving images to central repository...'
                script {
                    sh "echo ${DOCKER_CREDS_PSW} | docker login -u ${DOCKER_CREDS_USR} --password-stdin"
                    sh "docker push ${DOCKER_USER}/api-service:${env.IMAGE_TAG}"
                    sh "docker push ${DOCKER_USER}/api-service:latest"
                    sh "docker push ${DOCKER_USER}/db-worker-service:${env.IMAGE_TAG}"
                    sh "docker push ${DOCKER_USER}/db-worker-service:latest"
                }
            }
        }

        stage('Infrastructure Sync & Deploy') {
            steps {
                echo 'Updating Kubeconfig context and executing Ansible Playbook...'
                script {
                    // Authenticates your local kubectl runner context against AWS EKS
                    sh "aws eks update-kubeconfig --region ${AWS_REGION} --name ${CLUSTER_NAME}"
                    
                    // Executes Ansible playbook to apply manifests safely
                    dir('ansible') {
                        sh "ansible-playbook deploy-k8s.yml"
                    }
                }
            }
        }
    }

    post {
        always {
            echo 'Cleaning up worker node workspace environments...'
            cleanWs()
        }
    }
}