
pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        AWS_REGION       = 'ap-south-1'
        EKS_CLUSTER_NAME = 'tea-house-eks'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm

                script {
                    if (!fileExists('VERSION')) {
                        error('VERSION file is missing.')
                    }

                    def baseVersion = readFile('VERSION').trim()

                    if (!(baseVersion ==~ /^\d+\.\d+\.\d+$/)) {
                        error("Invalid VERSION: ${baseVersion}")
                    }

                    env.BASE_VERSION = baseVersion
                    env.VERSION = "v${baseVersion}-${env.BUILD_NUMBER}"

                    echo "Tea House version: ${env.VERSION}"
                }
            }
        }

        stage('Preflight') {
            steps {
                sh '''
                    set -eu

                    echo "Checking Ansible..."
                    command -v ansible-playbook
                    command -v ansible-galaxy
                    command -v python3

                    ansible-playbook --version

                    /usr/bin/python3 -c \
                        "import kubernetes, yaml, jsonpatch"

                    EXPECTED_VERSION="$(
                        /usr/bin/python3 -c '
import yaml

with open("ansible/requirements.yml", encoding="utf-8") as f:
    data = yaml.safe_load(f)

matches = [
    item for item in data.get("collections", [])
    if item.get("name") == "kubernetes.core"
]

if len(matches) != 1 or not matches[0].get("version"):
    raise SystemExit(
        "Pin exactly one kubernetes.core version in requirements.yml"
    )

print(matches[0]["version"])
'
                    )"

                    ansible-galaxy collection list kubernetes.core \
                        > collection-list.txt

                    EXPECTED_VERSION="$EXPECTED_VERSION" \
                    COLLECTION_LIST="collection-list.txt" \
                    /usr/bin/python3 -c '
import os
from pathlib import Path

expected = os.environ["EXPECTED_VERSION"]
lines = Path(os.environ["COLLECTION_LIST"]).read_text().splitlines()

installed = any(
    len(parts := line.split()) >= 2
    and parts[0] == "kubernetes.core"
    and parts[1] == expected
    for line in lines
)

if not installed:
    raise SystemExit(
        f"Required kubernetes.core {expected} is not installed. "
        "Install it on the Jenkins host before deploying."
    )

print(f"kubernetes.core {expected} is available.")
'

                    command -v terraform
                    command -v docker
                    command -v aws
                    command -v kubectl
                    command -v curl

                    docker info >/dev/null

                    echo "Preflight passed."
                '''
            }
        }

        stage('Test API Service') {
            steps {
                sh '''
                    set -eu

                    docker run --rm \
                        -e PYTHONPATH=/app \
                        -v "$WORKSPACE/api-service:/app" \
                        -w /app \
                        python:3.11-slim \
                        sh -ec '
                            python -m pip install \
                                --disable-pip-version-check \
                                -r requirements.txt pytest
                            python -m pytest -q
                        '
                '''
            }
        }

        stage('Test DB Worker Service') {
            steps {
                sh '''
                    set -eu

                    docker run --rm \
                        -e PYTHONPATH=/app \
                        -v "$WORKSPACE/db-worker-service:/app" \
                        -w /app \
                        python:3.11-slim \
                        sh -ec '
                            python -m pip install \
                                --disable-pip-version-check \
                                -r requirements.txt pytest
                            python -m pytest -q
                        '
                '''
            }
        }

        

        stage('Build and Push Images') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-token',
                        usernameVariable: 'DH_USER',
                        passwordVariable: 'DH_PASS'
                    )
                ]) {
                    sh '''
                        set -eu

                        echo "$DH_PASS" | docker login \
                            --username "$DH_USER" \
                            --password-stdin

                        trap 'docker logout >/dev/null 2>&1 || true' EXIT

                        docker build \
                            -t "$DH_USER/api-service:$VERSION" \
                            -t "$DH_USER/api-service:latest" \
                            ./api-service

                        docker build \
                            -t "$DH_USER/db-worker-service:$VERSION" \
                            -t "$DH_USER/db-worker-service:latest" \
                            ./db-worker-service

                        docker push "$DH_USER/api-service:$VERSION"
                        docker push "$DH_USER/api-service:latest"

                        docker push "$DH_USER/db-worker-service:$VERSION"
                        docker push "$DH_USER/db-worker-service:latest"
                    '''
                }
            }
        }

        
        // stage('Terraform Provisioning') {
        //     steps {
        //         withCredentials([
        //             string(
        //                 credentialsId: 'aws-access-key-id',
        //                 variable: 'AWS_ACCESS_KEY_ID'
        //             ),
        //             string(
        //                 credentialsId: 'aws-secret-access_key',
        //                 variable: 'AWS_SECRET_ACCESS_KEY'
        //             )
        //         ]) {
        //             dir('terraform') {
        //                 sh '''
        //                     set -eu
        //                     set +x

        //                     export AWS_DEFAULT_REGION="$AWS_REGION"

        //                     echo "STEP 1: Checking AWS identity"
        //                     aws sts get-caller-identity

        //                     echo "STEP 2: Terraform version"
        //                     terraform version

        //                     echo "STEP 3: Initializing Terraform"
        //                     terraform init -input=false -no-color

        //                     echo "STEP 4: Validating Terraform"
        //                     terraform validate -no-color

        //                     echo "STEP 5: Checking local state"
        //                     if [ -f terraform.tfstate ]; then
        //                         echo "State file exists."
        //                         terraform state list
        //                     else
        //                         echo "No local state file found."
        //                     fi

        //                     echo "STEP 6: Generating plan only"
        //                     terraform plan \
        //                         -input=false \
        //                         -no-color
        //                 '''
        //             }
        //         }
        //     }
        // }

        stage('Terraform Provisioning') {
            steps {
                script {
                    echo 'TERRAFORM DIAGNOSTIC: stage entered'
                }

                dir('terraform') {
                    sh '''
                        set +e
                        echo "TERRAFORM DIAGNOSTIC: shell started"
                        echo "Workspace: $WORKSPACE"
                        echo "Current directory: $(pwd)"
                        echo "Terraform executable: $(command -v terraform)"
                        terraform version
                        echo "Shell exit code: $?"
                        exit 0
                    '''
                }
            }
        }


        stage('Deploy and Verify') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'dockerhub-token',
                        usernameVariable: 'DH_USER',
                        passwordVariable: 'DH_PASS'
                    ),
                    string(
                        credentialsId: 'aws-access-key-id',
                        variable: 'AWS_ACCESS_KEY_ID'
                    ),
                    string(
                        credentialsId: 'aws-secret-access_key',
                        variable: 'AWS_SECRET_ACCESS_KEY'
                    ),
                    string(
                        credentialsId: 'postgres-user',
                        variable: 'POSTGRES_USER'
                    ),
                    string(
                        credentialsId: 'postgres-password',
                        variable: 'POSTGRES_PASSWORD'
                    ),
                    string(
                        credentialsId: 'postgres-db',
                        variable: 'POSTGRES_DB'
                    ),
                    string(
                        credentialsId: 'rabbitmq-user',
                        variable: 'RABBITMQ_USER'
                    ),
                    string(
                        credentialsId: 'rabbitmq-password',
                        variable: 'RABBITMQ_PASSWORD'
                    )
                ]) {
                    sh '''
                        set -eu
                        set +x

                        export AWS_DEFAULT_REGION="$AWS_REGION"

                        echo "Verifying AWS identity..."
                        aws sts get-caller-identity

                        echo "Configuring EKS access..."
                        aws eks update-kubeconfig \
                            --region "$AWS_REGION" \
                            --name "$EKS_CLUSTER_NAME"

                        kubectl cluster-info

                        export RABBITMQ_URL="$(
                            /usr/bin/python3 -c '
import os
from urllib.parse import quote

user = quote(os.environ["RABBITMQ_USER"], safe="")
password = quote(os.environ["RABBITMQ_PASSWORD"], safe="")

print(
    f"amqp://{user}:{password}"
    "@rabbitmq-service:5672/%2F"
)
'
                        )"

                        API_IMAGE="$DH_USER/api-service:$VERSION"
                        WORKER_IMAGE="$DH_USER/db-worker-service:$VERSION"

                        echo "Deploying version $VERSION..."

                        /usr/bin/ansible-playbook \
                            -i localhost, \
                            ansible/deploy-k8s.yml \
                            -e "api_image=$API_IMAGE" \
                            -e "worker_image=$WORKER_IMAGE"

                        echo "Waiting for API rollout..."
                        kubectl rollout status \
                            deployment/api-service \
                            --timeout=300s

                        echo "Waiting for worker rollout..."
                        kubectl rollout status \
                            deployment/db-worker-service \
                            --timeout=300s

                        echo "Waiting for LoadBalancer address..."

                        API_HOST=""

                        for attempt in $(seq 1 60); do
                            API_HOST="$(
                                kubectl get service api-service \
                                    -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
                            )"

                            if [ -z "$API_HOST" ]; then
                                API_HOST="$(
                                    kubectl get service api-service \
                                        -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
                                )"
                            fi

                            if [ -n "$API_HOST" ]; then
                                break
                            fi

                            echo "Waiting for external address ($attempt/60)"
                            sleep 5
                        done

                        if [ -z "$API_HOST" ]; then
                            kubectl get service api-service
                            echo "ERROR: LoadBalancer address was not assigned."
                            exit 1
                        fi

                        API_URL="http://$API_HOST/pulse"

                        echo "Checking external API health..."

                        RESPONSE="$(
                            curl \
                                --fail \
                                --show-error \
                                --silent \
                                --retry 12 \
                                --retry-delay 5 \
                                --retry-connrefused \
                                --max-time 10 \
                                "$API_URL"
                        )"

                        printf '%s\\n' "$RESPONSE" |
                            /usr/bin/python3 -c '
import json
import sys

data = json.load(sys.stdin)

if data.get("status") != "online":
    raise SystemExit(
        f"Unexpected health response: {data}"
    )

print("Public API health check passed.")
'

                        echo "Tea House $VERSION deployed successfully."
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "Deployment ${env.VERSION} succeeded."
        }

        failure {
            echo 'Pipeline failed. Inspect the failed stage logs.'
        }

        always {
            echo 'Pipeline finished.'
        }
    }
}
