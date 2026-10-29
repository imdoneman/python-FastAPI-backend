# Tea House Backend

**A six-branch, progressively evolved FastAPI backend project: from in-memory CRUD to a distributed, Kubernetes-deployed service with CI/CD and observability.**

[Repository](https://github.com/imdoneman/python-FastAPI-backend) · [Final implementation](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-4-monitoring)

## Project overview

Tea House is a learning-oriented backend engineering project that evolves the same tea-inventory domain through increasingly sophisticated architectures. The progression demonstrates REST API design, relational persistence, automated testing, containerization, infrastructure as code, remote deployments, asynchronous message processing, and observability.

The final iteration separates the HTTP API from the database worker, sends write commands through RabbitMQ, deploys services on AWS EKS using Jenkins/Terraform/Ansible, and exposes metrics to Prometheus and Grafana.

## Development roadmap

| Branch                                                                                                                                      | Focus                                         | Core change                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`main`](https://github.com/imdoneman/python-FastAPI-backend/tree/main)                                                                     | In-memory CRUD API and local Jenkins pipeline | A single FastAPI process stores teas in an in-memory list. Records are lost when the process restarts.                                                               |
| [`iteration-2`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2)                                                       | Persistent SQL CRUD API                       | The API uses SQLAlchemy sessions and database-backed tea records. Docker Compose starts the API and PostgreSQL with a database health check.                         |
| [`iteration-2-with-auto-provisioning`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2-with-auto-provisioning)         | Automatic AWS EC2 provisioning and deployment | Jenkins builds/tests the image, provisions an EC2 host with Terraform, transfers the image archive and uses Ansible to deploy the API and PostgreSQL stack.          |
| [`iteration-2-with-jenkins-registry-push`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2-with-jenkins-registry-push) | Registry-backed, versioned CI/CD              | Jenkins derives a versioned image tag, runs pytest, pushes to Docker Hub, provisions EC2, and deploys a registry image with Ansible.                                 |
| [`iteration-3-rabbitmq`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-3-rabbitmq)                                     | Asynchronous RabbitMQ processing on EKS       | Writes publish commands to RabbitMQ and return HTTP 202; a separate worker consumes messages and commits database changes. Reads proxy to the worker's internal API. |
| [`iteration-4-monitoring`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-4-monitoring)                                 | Prometheus and Grafana observability          | Extends the EKS deployment with application/worker metrics, ServiceMonitors, pinned Helm monitoring installation and infrastructure dashboards.                      |

> The branch names reflect historical development checkpoints, not a strictly numbered release sequence.

## Final architecture (Iteration 4)

```text
                      ┌───────────────────────┐
                      │       API client      │
                      └───────────┬───────────┘
                                  │ HTTP
                                  ▼
                         ┌─────────────────┐
                         │ FastAPI service │
                         │ /pulse /metrics │
                         └───────┬─────────┘
                                 │
                 ┌───────────────┴──────────────────┐
                 │ writes: publish                 │ reads: HTTP
                 ▼                                 ▼
         ┌─────────────────┐                ┌─────────────────────┐
         │ RabbitMQ queue  │                │ DB worker internal  │
         │ tea_tasks       │                │ GET /internal/teas  │
         └────────┬────────┘                └─────────┬───────────┘
                  │ consumer                          │
                  ▼                                   │
         ┌─────────────────┐                          │
         │ DB worker       │──────────────────────────┘
         │ /pulse /metrics │
         └────────┬────────┘
                  ▼
         ┌─────────────────┐
         │ PostgreSQL      │
         └─────────────────┘

         ServiceMonitors → Prometheus → Grafana
         Node Exporter ────────────────┘
```

The final deployment is hosted on **AWS EKS**; Jenkins orchestrates image builds/publication, Terraform provisions AWS infrastructure, and Ansible applies Kubernetes resources and installs the monitoring chart.

> **Security note** : HTTP endpoints shown in this documentation are intended for local development or controlled testing environments. Production-facing deployments should use HTTPS with TLS termination at an ingress controller or AWS load balancer. Internal Kubernetes traffic is not automatically encrypted.

## Technologies

| Layer                    | Technologies                                                |
| ------------------------ | ----------------------------------------------------------- |
| API                      | Python, FastAPI, Pydantic                                   |
| Persistence              | PostgreSQL, SQLAlchemy; SQLite fallback in earlier branches |
| Messaging                | RabbitMQ, Pika                                              |
| Containers               | Docker, Docker Compose (earlier branches)                   |
| CI/CD                    | Jenkins, Docker Hub                                         |
| Infrastructure           | AWS EC2 (intermediate branches), AWS EKS, Terraform         |
| Configuration/deployment | Ansible, Kubernetes manifests, Helm                         |
| Observability            | Prometheus, Grafana, Node Exporter, ServiceMonitor          |
| Tests                    | pytest, FastAPI test clients and mocked integrations        |

## API overview (latest branch)

| Method   | Path             | Semantics                                  |
| -------- | ---------------- | ------------------------------------------ |
| `GET`    | `/`              | Welcome                                    |
| `GET`    | `/pulse`         | API status/uptime                          |
| `GET`    | `/teas`          | Reads from worker's internal API           |
| `POST`   | `/teas`          | Queues creation (`202`)                    |
| `POST`   | `/teas/bulk`     | Queues bulk creation (`202`)               |
| `PUT`    | `/teas/{tea_id}` | Queues update (`202`)                      |
| `DELETE` | `/teas/{tea_id}` | Queues deletion (`202`)                    |
| `GET`    | `/metrics`       | Prometheus instrumentation (latest branch) |

Example write payload:

```json
{ "name": "Darjeeling First Flush", "origin": "India" }
```

**Important:** In Iterations 3–4, `202 Accepted` means the RabbitMQ message was accepted for processing; it does **not** mean the database transaction has completed. Earlier branches perform synchronous writes.

## Getting started

Choose the branch matching your goal:

- **Fastest local demo:** `main` — install requirements, run pytest, then start Uvicorn.
- **Database-backed local stack:** `iteration-2` — `docker compose -f docker-compose.yaml up --build`.
- **AWS EC2 automation:** `iteration-2-with-auto-provisioning` or `iteration-2-with-jenkins-registry-push`.
- **EKS distributed architecture:** `iteration-3-rabbitmq`.
- **Full monitoring:** `iteration-4-monitoring`.

Each branch has its **own README** with architecture, commands, prerequisites and caveats. The cloud branches require Jenkins credentials, AWS IAM permissions, Docker registry access and active AWS infrastructure. Do not run their deployment pipelines without reviewing cost and security implications.

## CI/CD and infrastructure lifecycle

The project progresses from a local Jenkins build/test/deploy pipeline to a remote EC2 deployment, Docker Hub publishing, and finally an EKS pipeline that builds and pushes two images. Terraform and Ansible are deliberately kept separate: Terraform provisions infrastructure; Ansible configures/deploys the workloads.

**Destroying AWS resources:** use the original Terraform state from the provisioning workspace, run `terraform plan -destroy`, then `terraform destroy`. Check for Kubernetes-created load balancers and orphaned storage that Terraform might not manage.

## Monitoring and validation

The final branch includes FastAPI HTTP instrumentation, worker message counters and Node Exporter metrics. Prometheus discovers application metrics through ServiceMonitors; Grafana displays metrics and Kubernetes infrastructure dashboards.

Useful PromQL:

```promql
up{job=~".*node-exporter.*"}
up{service="db-worker-service"}
sum by (action, outcome) (tea_worker_messages_total)
sum by (action, outcome) (increase(tea_worker_messages_total[10m]))
```

The recorded deployment **`v4.2.0-6`** completed successfully through Jenkins. Subsequent manual validation confirmed both Node Exporter targets `UP`, FastAPI request metrics, worker metrics, and an acknowledged `create` operation. These observations establish the core metrics pipeline, **not** alert-notification delivery or long-term monitoring persistence.

## Engineering decisions and trade-offs

- **Synchronous → asynchronous writes:** decouples HTTP request handling from database mutation, but introduces eventual consistency and delivery/retry concerns.
- **Single app → API and worker services:** separates request handling and message consumption, at the cost of more components and operational complexity.
- **EC2 → EKS:** adds orchestration, service discovery and deployment controls while increasing cloud cost and configuration complexity.
- **Manual inspection → Prometheus/Grafana:** adds observability through metric scraping, though metrics alone do not replace distributed tracing or production-grade alert verification.
- **Versioned CI/CD:** produces traceable image tags; the latest `VERSION` file is `4.2.0`, while the API's `/pulse` response still reports `3.1.0`.

## Security and scope

This is a portfolio/educational project, not a claim of production hardening. Do not expose PostgreSQL, RabbitMQ, internal worker endpoints, Grafana credentials, Terraform state or deployment secrets. Some earlier Compose examples use demonstration credentials. Review AWS permissions, secret management, storage retention, cost, backups, availability and network exposure before deploying outside a controlled environment.

## Branch documentation

- [`main`](https://github.com/imdoneman/python-FastAPI-backend/tree/main) — In-memory CRUD API and local Jenkins pipeline
- [`iteration-2`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2) — Persistent SQL CRUD API
- [`iteration-2-with-auto-provisioning`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2-with-auto-provisioning) — Automatic AWS EC2 provisioning and deployment
- [`iteration-2-with-jenkins-registry-push`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2-with-jenkins-registry-push) — Registry-backed, versioned CI/CD
- [`iteration-3-rabbitmq`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-3-rabbitmq) — Asynchronous RabbitMQ processing on EKS
- [`iteration-4-monitoring`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-4-monitoring) — Prometheus and Grafana observability

## Project status

**Development completed.** The final iteration was deployed and its core monitoring metrics verified. The cloud infrastructure was subsequently decommissioned to avoid ongoing AWS costs, while the source code, infrastructure configuration, and project documentation remain available in this repository.
