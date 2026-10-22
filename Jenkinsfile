
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        APP_NAME             = "${env.GLOBAL_APP_NAME}"
        DOCKER_REGISTRY_USER = "${env.GLOBAL_DOCKER_USER}"
        AWS_REGION           = 'ap-south-1'

        AWS_SSH_KEY_CRED_ID  = 'fastapi-aws-ssh-key'
        DOCKERHUB_CRED_ID    = 'dockerhub-token'
        AWS_ACCESS_CRED_ID   = 'aws-access-key-id'
        AWS_SECRET_CRED_ID   = 'aws-secret-access-key'
        DB_PASSWORD_CRED_ID  = 'production-db-password'
    }

    stages {
        stage('Checkout') {
            steps {
                git branch: 'iteration-2-with-jenkins-registry-push',
                    url: 'https://github.com/imdoneman/python-FastAPI-backend.git'

                sh '''
                    set -eu
                    test -f Dockerfile
                    test -f requirements.txt
                    test -f requirements-dev.txt
                    test -f VERSION
                    test -f docker-compose.yaml
                    test -f terraform/main.tf
                    test -f ansible/playbook.yml
                '''
            }
        }

        stage('Determine Version') {
            steps {
                script {
                    def codeVersion = readFile('VERSION').trim()

                    if (!(codeVersion ==~ /[0-9A-Za-z][0-9A-Za-z._-]*/)) {
                        error "Invalid VERSION value: ${codeVersion}"
                    }

                    env.IMAGE_TAG = "v${codeVersion}-${env.BUILD_NUMBER}"
                    env.IMAGE_REF =
                        "${env.DOCKER_REGISTRY_USER}/${env.APP_NAME}:${env.IMAGE_TAG}"
                    env.LATEST_REF =
                        "${env.DOCKER_REGISTRY_USER}/${env.APP_NAME}:latest"

                    echo "Locked in deployment tag: ${env.IMAGE_TAG}"
                }
            }
        }

        stage('Execute Pytest Suite') {
            steps {
                sh '''
                    set -eu

                    python3 -m venv .venv
                    . .venv/bin/activate

                    python -m pip install --upgrade pip
                    pip install -r requirements-dev.txt
                    pytest test_main.py -v
                '''
            }
        }

        stage('Build & Push to Docker Hub') {
            steps {
                sh '''
                    set -eu

                    docker build \
                        --target runner \
                        --tag "$IMAGE_REF" \
                        .

                    docker tag "$IMAGE_REF" "$LATEST_REF"
                '''

                withCredentials([
                    usernamePassword(
                        credentialsId: "${env.DOCKERHUB_CRED_ID}",
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {
                    sh '''
                        set -eu

                        if [ "$DOCKER_USER" != "$DOCKER_REGISTRY_USER" ]; then
                            echo "Docker Hub credential username does not match GLOBAL_DOCKER_USER."
                            exit 1
                        fi

                        DOCKER_CONFIG=$(mktemp -d)
                        export DOCKER_CONFIG

                        cleanup_docker_auth() {
                            docker logout >/dev/null 2>&1 || true
                            rm -rf "$DOCKER_CONFIG"
                        }
                        trap cleanup_docker_auth EXIT

                        printf '%s' "$DOCKER_PASS" |
                            docker login \
                                --username "$DOCKER_USER" \
                                --password-stdin

                        docker push "$IMAGE_REF"
                        docker push "$LATEST_REF"
                    '''
                }
            }
        }

        stage('Provision Infrastructure (Terraform)') {
            steps {
                echo 'Provisioning AWS infrastructure with Terraform...'

                withCredentials([
                    string(
                        credentialsId: "${env.AWS_ACCESS_CRED_ID}",
                        variable: 'AWS_ACCESS_KEY_ID'
                    ),
                    string(
                        credentialsId: "${env.AWS_SECRET_CRED_ID}",
                        variable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    withEnv(["AWS_DEFAULT_REGION=${env.AWS_REGION}"]) {
                        sh '''
                            set -eu

                            terraform -chdir=terraform init
                            terraform -chdir=terraform validate
                            terraform -chdir=terraform plan -out=tfplan
                            terraform -chdir=terraform apply -auto-approve tfplan
                        '''

                        script {
                            env.EC2_IP = sh(
                                script: 'terraform -chdir=terraform output -raw server_public_ip',
                                returnStdout: true
                            ).trim()

                            env.SSH_USER = sh(
                                script: 'terraform -chdir=terraform output -raw ssh_username',
                                returnStdout: true
                            ).trim()

                            if (!env.EC2_IP || !env.SSH_USER) {
                                error 'Terraform did not return the EC2 IP and SSH username.'
                            }

                            echo "Provisioned EC2 address: ${env.EC2_IP}"
                            echo "EC2 SSH username: ${env.SSH_USER}"
                        }
                    }
                }
            }
        }

        stage('Ansible Production Deployment') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: "${env.AWS_SSH_KEY_CRED_ID}",
                        keyFileVariable: 'SSH_KEY_PATH',
                        usernameVariable: 'SSH_CREDENTIAL_USER'
                    ),
                    string(
                        credentialsId: "${env.DB_PASSWORD_CRED_ID}",
                        variable: 'DB_PASS'
                    )
                ]) {
                    sh '''
                        set -eu

                        mkdir -p "$HOME/.ssh"
                        chmod 700 "$HOME/.ssh"

                        if [ "$SSH_CREDENTIAL_USER" != "$SSH_USER" ]; then
                            echo "SSH credential username does not match Terraform's SSH username."
                            exit 1
                        fi

                        CONNECTED=false

                        for attempt in $(seq 1 30); do
                            if ssh \
                                -i "$SSH_KEY_PATH" \
                                -o BatchMode=yes \
                                -o ConnectTimeout=5 \
                                -o StrictHostKeyChecking=accept-new \
                                "${SSH_USER}@${EC2_IP}" \
                                'true'; then
                                CONNECTED=true
                                break
                            fi

                            echo "Waiting for EC2 SSH ($attempt/30)..."
                            sleep 10
                        done

                        if [ "$CONNECTED" != true ]; then
                            echo "EC2 SSH connection did not become available."
                            exit 1
                        fi

                        # Put sensitive variables in a temporary file instead
                        # of exposing the database password in process arguments.
                        VARS_FILE=$(mktemp)
                        chmod 600 "$VARS_FILE"

                        cleanup_ansible_vars() {
                            rm -f "$VARS_FILE"
                        }
                        trap cleanup_ansible_vars EXIT

                        export TARGET_DB_PASSWORD="$DB_PASS"

                        python3 - "$VARS_FILE" <<'PY'
import json
import os
import sys

variables = {
    "app_name": os.environ["APP_NAME"],
    "docker_registry_user": os.environ["DOCKER_REGISTRY_USER"],
    "docker_image_tag": os.environ["IMAGE_TAG"],
    "target_db_user": "admin",
    "target_db_password": os.environ["TARGET_DB_PASSWORD"],
    "target_db_name": "tea_house",
}

with open(sys.argv[1], "w", encoding="utf-8") as file:
    json.dump(variables, file)
PY

                        ansible-playbook \
                            -i "${EC2_IP}," \
                            ansible/playbook.yml \
                            -u "$SSH_USER" \
                            --private-key "$SSH_KEY_PATH" \
                            --extra-vars "@$VARS_FILE"
                    '''
                }
            }
        }

        stage('Verify Remote API') {
            steps {
                sh '''
                    set -eu

                    RESPONSE=""

                    for attempt in $(seq 1 12); do
                        RESPONSE=$(curl \
                            --silent \
                            --show-error \
                            --fail \
                            --max-time 10 \
                            "http://${EC2_IP}:8000/pulse" \
                            2>/dev/null) || RESPONSE=""

                        if printf '%s' "$RESPONSE" |
                            grep -q '"status"[[:space:]]*:[[:space:]]*"online"'; then
                            echo "Remote health check passed:"
                            echo "$RESPONSE"
                            exit 0
                        fi

                        echo "Waiting for API health ($attempt/12)..."
                        sleep 5
                    done

                    echo "Remote API health check failed."
                    exit 1
                '''
            }
        }
    }

    post {
        success {
            echo "Deployment successful: ${env.IMAGE_REF}"
            echo "API endpoint: http://${env.EC2_IP}:8000/pulse"
        }

        failure {
            echo 'Pipeline failed. Review the stage logs before retrying.'
        }

        always {
            sh '''
                set +e

                if [ -n "${IMAGE_REF:-}" ]; then
                    docker image rm "$IMAGE_REF" >/dev/null 2>&1
                fi

                if [ -n "${LATEST_REF:-}" ]; then
                    docker image rm "$LATEST_REF" >/dev/null 2>&1
                fi

                rm -f terraform/tfplan
                rm -rf .venv
            '''
        }
    }
}
