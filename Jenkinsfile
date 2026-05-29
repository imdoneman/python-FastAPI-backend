pipeline {
    agent any

    environment {
        APP_NAME             = "${env.GLOBAL_APP_NAME}"
        DOCKER_REGISTRY_USER = "${env.GLOBAL_DOCKER_USER}"
        IMAGE_TAG            = "v${BUILD_NUMBER}"
        
        AWS_SSH_KEY_CRED_ID  = 'fastapi-aws-ssh-key'
        DOCKERHUB_CRED_ID    = 'dockerhub-token'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'iteration-2-with-jenkins-registry-push',
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

        stage('Execute Pytest Suite') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -r requirements.txt pytest httpx
                    pytest test_main.py -v
                '''
            }
        }

        stage('Build & Push to Docker Hub') {
            steps {
                sh "docker build -t ${env.DOCKER_REGISTRY_USER}/${env.APP_NAME}:${env.IMAGE_TAG} ."
                sh "docker tag ${env.DOCKER_REGISTRY_USER}/${env.APP_NAME}:${env.IMAGE_TAG} ${env.DOCKER_REGISTRY_USER}/${env.APP_NAME}:latest"

                withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CRED_ID, usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
                    sh "echo \$DOCKER_PASS | docker login -u \$DOCKER_USER --password-stdin"
                    sh "docker push ${env.DOCKER_REGISTRY_USER}/${env.APP_NAME}:${env.IMAGE_TAG}"
                    sh "docker push ${env.DOCKER_REGISTRY_USER}/${env.APP_NAME}:latest"
                }
            }
        }

        // ... (Previous stages: Checkout, Test, Docker Build & Push) ...

        stage('Provision Infrastructure (Terraform)') {
            steps {
                echo 'Spinning up AWS hardware via Terraform...'
                
                // Inject AWS API keys directly into the execution environment
                withCredentials([
                    string(credentialsId: 'aws-access-key-id', variable: 'AWS_ACCESS_KEY_ID'),
                    string(credentialsId: 'aws-secret-access-key', variable: 'AWS_SECRET_ACCESS_KEY')
                ]) {
                    sh '''
                        cd terraform/
                        
                        # Initialize the backend and provider plugins
                        terraform init
                        
                        # Apply the infrastructure stack bypassing the manual 'yes' prompt
                        terraform apply -auto-approve
                    '''
                }
            }
        }

        stage('Ansible Production Deployment') {
            steps {
                withCredentials([
                    sshUserPrivateKey(credentialsId: env.AWS_SSH_KEY_CRED_ID, keyFileVariable: 'SSH_KEY_PATH'),
                    string(credentialsId: 'production-db-password', variable: 'DB_PASS')
                ]) {
                    sh """
                        cd ansible/
                        export ANSIBLE_HOST_KEY_CHECKING=False
                        ansible-playbook -i hosts playbook.yml \
                          --private-key=\${SSH_KEY_PATH} \
                          -u ec2-user \
                          --extra-vars "docker_registry_user=${env.DOCKER_REGISTRY_USER} docker_image_tag=${env.IMAGE_TAG} target_db_user=admin target_db_password=\${DB_PASS} target_db_name=tea_house"
                    """
                }
            }
        }
    }
    post {
        always {
            sh "docker image prune -a -f || true"
        }
    }
}