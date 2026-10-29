# Tea House Backend — `iteration-2-with-auto-provisioning`

> **Branch 3 of 6 · Automatic AWS EC2 provisioning and deployment**

[Project repository](https://github.com/imdoneman/python-FastAPI-backend) · [Browse this branch](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2-with-auto-provisioning)

## Purpose

Jenkins builds/tests the image, provisions an EC2 host with Terraform, transfers the image archive and uses Ansible to deploy the API and PostgreSQL stack.

The branch sequence is documented in the [project overview](https://github.com/imdoneman/python-FastAPI-backend#development-roadmap).

## Technology stack

Terraform, AWS EC2, Ansible, Jenkins, Docker Compose

## Architecture

```text
Jenkins
  ├── Build Docker image
  ├── Save image as .tar
  ├── Terraform → Provision EC2
  └── SCP → Transfer image to EC2
                    │
                    ▼
              Ansible
                    │
                    ▼
          Load Docker image
                    │
                    ▼
            Docker Compose
             ├── FastAPI
             └── PostgreSQL
```

The EC2 host is created by Terraform; Ansible installs/configures the runtime and deploys the Compose stack.

This branch transfers the already-built Docker image archive to EC2 rather than requiring a public container registry.
## API contract

| Method | Endpoint | Behavior |
|---|---|---|
| `GET` | `/` | Welcome message |
| `GET` | `/pulse` | Status, uptime, application version |
| `GET` | `/teas` | List stored teas |
| `POST` | `/teas` | Create a tea; `201` |
| `POST` | `/teas/bulk` | Insert a batch; `201` for nonempty successful batches |
| `PUT` | `/teas/{tea_id}` | Update an existing tea |
| `DELETE` | `/teas/{tea_id}` | Delete an existing tea |

**Tea request example:**

```json
{"name": "Darjeeling First Flush", "origin": "India"}
```

```bash
curl -X POST http://localhost:8000/teas \
  -H 'Content-Type: application/json' \
  -d '{"name":"Darjeeling First Flush","origin":"India"}'
```

For this branch, successful writes are performed synchronously.

## Setup and operation

### Deployment prerequisites

- Jenkins agent with Docker, Terraform, Ansible, AWS CLI, SSH access and the required Jenkins credentials.
- AWS permissions for the Terraform resources defined in `terraform/main.tf`.
- A configured EC2 SSH key and network access appropriate to the pipeline.
- Replace demonstration database credentials before public deployment.

Inspect the `Jenkinsfile` **environment and credentials references** and `terraform/` variables before running the job. Trigger the pipeline through Jenkins rather than assuming `docker compose up` provisions AWS.

To tear down infrastructure, run Terraform from the **same workspace and state** used to provision it:

```bash
cd terraform
terraform plan -destroy
terraform destroy
```

Check for non-Terraform AWS resources before assuming teardown is complete.


## Testing

```bash
pip install -r requirements.txt
pytest -q
```

The tests cover CRUD operations, invalid input, duplicate-name conflicts where applicable, and bulk-operation behavior. For CI specifics, inspect the branch's `Jenkinsfile`.

## Repository files in this branch

- `.dockerignore`
- `.gitattributes`
- `.gitignore`
- `Dockerfile`
- `Jenkinsfile`
- `ansible/playbook.yml`
- `database.py`
- `docker-compose.yaml`
- `main.py`
- `models.py`
- `requirements.txt`
- `schemas.py`
- `terraform/main.tf`
- `test_main.py`

## Security and operational notes

- Do not commit production secrets, Terraform state, SSH private keys or Jenkins credential values.
- Check any committed sample credentials or configuration before using the branch outside a development environment.
- Database schema creation and deployment are branch-specific; do not assume production migrations or high availability are implemented.
- This is an educational/portfolio implementation. AWS cost, IAM scope, data persistence and runtime security require review before production use.

## What changed in this iteration

Automatic AWS EC2 provisioning and deployment. Jenkins builds/tests the image, provisions an EC2 host with Terraform, transfers the image archive and uses Ansible to deploy the API and PostgreSQL stack.

Compare with the preceding branch: [`iteration-2`](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2).

## Navigation

[All branches and project evolution](https://github.com/imdoneman/python-FastAPI-backend) · [Source code for this branch](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2-with-auto-provisioning)
