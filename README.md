# ShopLedger

A customer-balance API for a retail shop, used as an end-to-end DevOps lab. The app is small on
purpose. The project is everything around it: how it is built, tested, deployed, watched and
recovered.

| Area | Tools |
|---|---|
| Lab | VirtualBox, Ubuntu Server 24.04, systemd |
| Source control | Git, GitHub |
| Configuration | Ansible |
| Containers | Docker, Docker Compose, Docker Hub, Trivy |
| CI/CD | Jenkins |
| Orchestration | Kubernetes (k3s), Kustomize, Helm, Traefik |
| Monitoring | Prometheus, Grafana, Alertmanager |
| Cloud | AWS (VPC, EC2, S3, Budgets), Terraform |

## Results

Fill this in from your own runs. Every line here should be something you can show.

- Commit to production: __ minutes
- Automatic rollback tested on: __
- Alert fired and resolved on: __

## Layout

    app/         Flask application
    tests/       Unit tests
    scripts/     Deploy, smoke test, load test, health check
    ansible/     Configures every VM
    k8s/         Kubernetes base and two overlays
    monitoring/  Helm values, alerts, dashboard
    terraform/   AWS infrastructure
    Jenkinsfile  The CI/CD pipeline

## Quick start

    cp .env.example .env
    docker compose up --build --detach --wait
    scripts/smoke-test.sh http://127.0.0.1:8000
