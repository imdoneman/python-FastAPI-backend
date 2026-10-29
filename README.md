# Tea House Backend — `iteration-4-monitoring`

> **Branch 6 of 6 · Prometheus and Grafana observability**

[Project repository](https://github.com/imdoneman/python-FastAPI-backend) · [Browse this branch](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-4-monitoring)

## Purpose

Extends the EKS deployment with application/worker metrics, ServiceMonitors, pinned Helm monitoring installation and infrastructure dashboards.

The branch sequence is documented in the [project overview](https://github.com/imdoneman/python-FastAPI-backend#development-roadmap).

## Technology stack

Prometheus, Grafana, kube-prometheus-stack, ServiceMonitor, Node Exporter, FastAPI, RabbitMQ, EKS

## Architecture

```text
Client → FastAPI API ──publish──→ RabbitMQ queue `tea_tasks`
             │                           │
             │ GET /teas                 ▼
             └──HTTP──→ DB worker API + consumer → PostgreSQL
                         (internal /internal/teas)

Jenkins → Docker Hub → Terraform (EKS/VPC) → Ansible → Kubernetes
```

Write endpoints acknowledge **queue acceptance**, not database commit. `202 Accepted` does not guarantee the command has already completed. The worker acknowledges successfully processed messages, rejects malformed commands, and may requeue transient failures.

```text
API /metrics ──────────┐
Worker /metrics ───────┼→ ServiceMonitors → Prometheus → Grafana
EKS node exporters ────┘
```
## API contract

| Method | Endpoint | Behavior |
|---|---|---|
| `GET` | `/` | Welcome message |
| `GET` | `/pulse` | API health/status |
| `GET` | `/teas` | Proxy read to the internal worker service |
| `POST` | `/teas` | Queue `create`; returns `202 Accepted` |
| `POST` | `/teas/bulk` | Queue `bulk_create`; returns `202 Accepted` |
| `PUT` | `/teas/{tea_id}` | Queue `update`; returns `202 Accepted` |
| `DELETE` | `/teas/{tea_id}` | Queue `delete`; returns `202 Accepted` |

**Tea request example:**

```json
{"name": "Darjeeling First Flush", "origin": "India"}
```

```bash
curl -X POST http://localhost:8000/teas \
  -H 'Content-Type: application/json' \
  -d '{"name":"Darjeeling First Flush","origin":"India"}'
```

The response confirms **queued work**; query `/teas` later to observe eventual database state.

## Setup and operation

### Deployment prerequisites

- AWS CLI access to `ap-south-1`, IAM permissions for the EKS/VPC resources, and sufficient AWS service quotas.
- Jenkins with Docker, Terraform, Ansible, `kubectl`, Helm, AWS CLI and configured registry/AWS credentials.
- Ansible Kubernetes collection dependencies specified in `ansible/requirements.yml`.
- Runtime PostgreSQL and RabbitMQ credentials supplied securely through the pipeline/Ansible configuration.

The pipeline provisions EKS, publishes **separate API and worker images**, then deploys Kubernetes resources via `ansible/deploy-k8s.yml`. Review its credential references and all Terraform inputs before triggering a run. Infrastructure incurs AWS charges.

For a deployed cluster, access the API using the exposure mechanism in `k8s-manifests/api-service.yaml`; for internal debugging use `kubectl port-forward`. Never expose PostgreSQL, RabbitMQ or worker internal endpoints publicly.

**Teardown:** use the original Terraform state and remove any Kubernetes-created AWS load balancers that block VPC deletion. Inspect persistent volumes and AWS EBS resources separately.

### Grafana access (through a host with EKS `kubectl` access)

```bash
kubectl -n monitoring port-forward svc/tea-house-monitoring-grafana 3000:80
```

If that host is remote, tunnel local port `3000` to its loopback port over SSH. Visit `http://localhost:3000`. Retrieve the admin password from the `tea-house-monitoring-grafana` Kubernetes Secret; do not publish it.

The Helm chart is pinned to `kube-prometheus-stack` **92.14.1**. The playbook labels both the application and `monitoring` namespaces for ServiceMonitor discovery.

#### Useful PromQL

```promql
up{job=~".*node-exporter.*"}
node_cpu_seconds_total
node_memory_MemAvailable_bytes
up{service="db-worker-service"}
sum by (action, outcome) (tea_worker_messages_total)
sum by (action, outcome) (increase(tea_worker_messages_total[10m]))
```

The worker counter includes actions `create`, `bulk_create`, `update`, `delete`, `invalid` and outcomes `acknowledged`, `rejected`, `requeued`. A `0` is normal until activity occurs. `increase()` extrapolates and may return non-integer values for integer counter increments.

**Observed validation:** Jenkins deployment `v4.2.0-6` succeeded; both node-exporter targets reported `up=1`, API and worker metrics were scraped, and a `create`/`acknowledged` counter increment was observed. This does not establish alert-delivery or persistence testing.


## Testing

Tests are separated by service:

```bash
python -m pip install -r api-service/requirements.txt
python -m pytest -q api-service/tests
python -m pip install -r db-worker-service/requirements.txt
python -m pytest -q db-worker-service/tests
```

Run the two suites in isolated virtual environments or containers if dependency versions conflict. The Jenkinsfile runs service-specific tests before image publication and infrastructure deployment. Tests mock external dependencies where appropriate.

**Version distinction:** `VERSION` contains `4.2.0` for pipeline image tagging, while the API `/pulse` handler reports `3.1.0`.

## Repository files in this branch

- `.gitattributes`
- `.gitignore`
- `Jenkinsfile`
- `VERSION`
- `ansible/ansible.cfg`
- `ansible/deploy-k8s.yml`
- `ansible/requirements.yml`
- `api-service/.dockerignore`
- `api-service/Dockerfile`
- `api-service/main.py`
- `api-service/producer.py`
- `api-service/requirements.txt`
- `api-service/schemas.py`
- `api-service/tests/test_main.py`
- `db-worker-service/.dockerignore`
- `db-worker-service/Dockerfile`
- `db-worker-service/database.py`
- `db-worker-service/models.py`
- `db-worker-service/requirements.txt`
- `db-worker-service/tests/test_database.py`
- `db-worker-service/worker.py`
- `k8s-manifests/api-service.yaml`
- `k8s-manifests/api-servicemonitor.yaml`
- `k8s-manifests/db-worker-service.yaml`
- `k8s-manifests/postgres.yaml`
- `k8s-manifests/rabbitmq.yaml`
- `k8s-manifests/worker-servicemonitor.yaml`
- `terraform/eks.tf`

## Security and operational notes

- Do not commit production secrets, Terraform state, SSH private keys or Jenkins credential values.
- Check any committed sample credentials or configuration before using the branch outside a development environment.
- Database schema creation and deployment are branch-specific; do not assume production migrations or high availability are implemented.
- This is an educational/portfolio implementation. AWS cost, IAM scope, data persistence and runtime security require review before production use.

## What changed in this iteration

Prometheus and Grafana observability. Extends the EKS deployment with application/worker metrics, ServiceMonitors, pinned Helm monitoring installation and infrastructure dashboards.

Compare with the preceding branch: [`iteration-3-rabbitmq`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-3-rabbitmq).

## Navigation

[All branches and project evolution](https://github.com/imdoneman/python-FastAPI-backend) · [Source code for this branch](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-4-monitoring)
