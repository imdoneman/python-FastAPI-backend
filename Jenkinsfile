
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        APP_NAME   = 'tea-house-api'
        IMAGE_TAG  = '2.2.0'
        AWS_REGION = 'ap-south-1'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm

                sh '''
                    set -eu
                    test -f Dockerfile
                    test -f docker-compose.yaml
                    test -f terraform/main.tf
                    test -f ansible/playbook.yml
                '''
            }
        }

        stage('Build and Test Image') {
            steps {
                sh '''
                    set -eu

                    IMAGE_NAME="${APP_NAME}:${IMAGE_TAG}"
                    IMAGE_ARCHIVE="${APP_NAME}-${IMAGE_TAG}.tar"

                    docker build \
                        --target runner \
                        --tag "$IMAGE_NAME" \
                        .

                    docker image save \
                        --output "$IMAGE_ARCHIVE" \
                        "$IMAGE_NAME"

                    test -s "$IMAGE_ARCHIVE"
                '''
            }
        }

        stage('Provision EC2') {
            steps {
                withCredentials([
                    string(
                        credentialsId: 'aws-access-key-id',
                        variable: 'AWS_ACCESS_KEY_ID'
                    ),
                    string(
                        credentialsId: 'aws-secret-access-key',
                        variable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    script {
                        withEnv(["AWS_DEFAULT_REGION=${env.AWS_REGION}"]) {
                            sh '''
                                set -eu

                                terraform -chdir=terraform init
                                terraform -chdir=terraform validate
                                terraform -chdir=terraform plan \
                                    -out=tfplan
                                terraform -chdir=terraform apply \
                                    -auto-approve tfplan
                            '''

                            env.EC2_IP = sh(
                                script: 'terraform -chdir=terraform output -raw server_public_ip',
                                returnStdout: true
                            ).trim()

                            env.SSH_USER = sh(
                                script: 'terraform -chdir=terraform output -raw ssh_username',
                                returnStdout: true
                            ).trim()
                        }
                    }
                }

                echo "Provisioned EC2 address: ${env.EC2_IP}"
            }
        }

        stage('Deploy to EC2') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'fastapi-aws-ssh-key',
                        keyFileVariable: 'SSH_KEY_PATH',
                        usernameVariable: 'SSH_CREDENTIAL_USER'
                    )
                ]) {
                    sh '''
                        set -eu

                        mkdir -p "$HOME/.ssh"
                        chmod 700 "$HOME/.ssh"

                        # Confirm that the credential matches the EC2 login.
                        if [ "$SSH_CREDENTIAL_USER" != "$SSH_USER" ]; then
                            echo "SSH credential username does not match Terraform's SSH username."
                            exit 1
                        fi

                        # Wait for EC2 SSH to become available.
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

                        IMAGE_ARCHIVE="${APP_NAME}-${IMAGE_TAG}.tar"

                        ssh \
                            -i "$SSH_KEY_PATH" \
                            -o BatchMode=yes \
                            -o StrictHostKeyChecking=accept-new \
                            "${SSH_USER}@${EC2_IP}" \
                            'id; df -h /tmp; df -i /tmp; ls -ld /tmp; touch /tmp/jenkins-scp-test && rm /tmp/jenkins-scp-test'

                        # Transfer the already-built image archive.
                        scp \
                            -i "$SSH_KEY_PATH" \
                            -o BatchMode=yes \
                            -o StrictHostKeyChecking=accept-new \
                            "$IMAGE_ARCHIVE" \
                            "${SSH_USER}@${EC2_IP}:/tmp/${IMAGE_ARCHIVE}"

                        # Configure EC2 and deploy without rebuilding the API.
                        ansible-playbook \
                            -i "${EC2_IP}," \
                            ansible/playbook.yml \
                            -u "$SSH_USER" \
                            --private-key "$SSH_KEY_PATH" \
                            -e "tea_house_image_tag=${IMAGE_TAG}"
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
            echo "Deployment successful: ${APP_NAME}:${IMAGE_TAG}"
            echo "API endpoint: http://${env.EC2_IP}:8000/pulse"
        }

        failure {
            echo 'Pipeline failed. Review the stage logs before retrying.'
        }

        always {
            sh '''
                rm -f "${APP_NAME}-${IMAGE_TAG}.tar"
                rm -f terraform/tfplan
            '''
        }
    }
}
