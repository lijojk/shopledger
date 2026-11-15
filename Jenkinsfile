pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 45, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    triggers {
        // The lab is private, so GitHub cannot call a webhook. Jenkins polls instead.
        pollSCM('H/2 * * * *')
    }

    environment {
        IMAGE = 'lijodoker/shopledger'
        INGRESS_IP = '192.168.56.11'
        TAG = sh(script: 'git rev-parse --short=8 HEAD', returnStdout: true).trim()
    }

    stages {
        stage('Static checks') {
            parallel {
                stage('Shell') {
                    steps {
                        sh 'shellcheck scripts/*.sh'
                    }
                }
                stage('Dockerfile') {
                    steps {
                        sh '''
                            docker run --rm -i hadolint/hadolint:v2.12.0 \
                                hadolint --failure-threshold error - < Dockerfile
                        '''
                    }
                }
                stage('Ansible') {
                    steps {
                        sh 'cd ansible && ansible-playbook site.yml --syntax-check'
                    }
                }
                stage('Terraform') {
                    steps {
                        sh '''
                            terraform fmt -check -recursive terraform
                            export TF_PLUGIN_CACHE_DIR="$HOME/.terraform.d/plugin-cache"
                            mkdir -p "$TF_PLUGIN_CACHE_DIR"
                            terraform -chdir=terraform/live init -backend=false -input=false
                            terraform -chdir=terraform/live validate
                        '''
                    }
                }
                stage('Kubernetes') {
                    steps {
                        sh '''
                            kubectl kustomize k8s/overlays/staging > /dev/null
                            kubectl kustomize k8s/overlays/production > /dev/null
                        '''
                    }
                }
            }
        }

        stage('Unit tests') {
            steps {
                sh '''
                    docker build --target test --tag shopledger:test .
                    mkdir -p reports
                    docker run --rm --user "$(id -u):$(id -g)" \
                        --env COVERAGE_FILE=/tmp/.coverage \
                        --volume "$PWD/reports:/srv/reports" \
                        shopledger:test \
                        sh -c 'ruff check --no-cache app tests &&
                            pytest --junitxml=reports/junit.xml -p no:cacheprovider'
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'reports/junit.xml'
                }
            }
        }

        stage('Build image') {
            steps {
                sh 'docker build --target runtime --build-arg APP_VERSION="$TAG" --tag "$IMAGE:$TAG" .'
            }
        }

        stage('Scan image') {
            steps {
                sh '''
                    trivy image --severity CRITICAL --ignore-unfixed \
                        --exit-code 1 --no-progress "$IMAGE:$TAG"
                '''
            }
        }

        stage('Integration test') {
            environment {
                COMPOSE_PROJECT_NAME = 'shopledger-ci'
                WEB_PORT = '18000'
                APP_ENV = 'ci'
            }
            steps {
                sh '''
                    export DB_PASSWORD="$(openssl rand -hex 16)"
                    IMAGE="$IMAGE:$TAG" docker compose up --detach --wait --no-build
                    scripts/smoke-test.sh "http://127.0.0.1:$WEB_PORT"
                '''
            }
            post {
                always {
                    sh 'DB_PASSWORD=unused docker compose down --volumes || true'
                }
            }
        }

        stage('Push image') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub',
                    usernameVariable: 'REGISTRY_USER',
                    passwordVariable: 'REGISTRY_TOKEN'
                )]) {
                    sh '''
                        echo "$REGISTRY_TOKEN" | docker login --username "$REGISTRY_USER" --password-stdin
                        docker push "$IMAGE:$TAG"
                        docker logout
                    '''
                }
            }
        }

        stage('Deploy to staging') {
            steps {
                withCredentials([file(credentialsId: 'lab-kubeconfig', variable: 'KUBECONFIG')]) {
                    sh 'scripts/deploy.sh staging "$IMAGE" "$TAG"'
                }
            }
        }

        stage('Smoke test staging') {
            steps {
                sh 'scripts/smoke-test.sh "http://$INGRESS_IP" staging.shopledger.lab'
            }
        }

        stage('Approve production') {
            steps {
                timeout(time: 30, unit: 'MINUTES') {
                    input message: "Deploy ${env.TAG} to production?", ok: 'Deploy'
                }
            }
        }

        stage('Deploy to production') {
            steps {
                withCredentials([file(credentialsId: 'lab-kubeconfig', variable: 'KUBECONFIG')]) {
                    sh 'scripts/deploy.sh production "$IMAGE" "$TAG"'
                }
                sh '''
                    served=$(curl -fsS --header 'Host: shopledger.lab' \
                        "http://$INGRESS_IP/version" | jq -r .version)
                    test "$served" = "$TAG"
                '''
            }
        }
    }

    post {
        always {
            sh 'docker image prune --force --filter until=48h || true'
            cleanWs()
        }
        success {
            echo "Build ${env.TAG} is live in production."
        }
        failure {
            echo "Build ${env.TAG} failed. Open the first red stage to see why."
        }
    }
}
