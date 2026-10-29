# Tea House Backend — `main`

> **Branch 1 of 6 · In-memory CRUD API and local Jenkins pipeline**

[Project repository](https://github.com/imdoneman/python-FastAPI-backend) · [Browse this branch](https://github.com/imdoneman/python-FastAPI-backend/tree/main)

## Purpose

A single FastAPI process stores teas in an in-memory list. Records are lost when the process restarts.

The branch sequence is documented in the [project overview](https://github.com/imdoneman/python-FastAPI-backend#development-roadmap).

## Technology stack

Python/FastAPI, Pydantic, pytest, Docker, Jenkins

## Architecture

```text
HTTP client → FastAPI (in-memory tea list)
                    ↑
              pytest + Jenkins
```

There is **no persistent database** in this branch. Multiple process instances do not share the in-memory list.

## API contract

| Method   | Endpoint         | Behavior                                              |
| -------- | ---------------- | ----------------------------------------------------- |
| `GET`    | `/`              | Welcome message                                       |
| `GET`    | `/pulse`         | Status, uptime, application version                   |
| `GET`    | `/teas`          | List stored teas                                      |
| `POST`   | `/teas`          | Create a tea; `201`                                   |
| `POST`   | `/teas/bulk`     | Insert a batch; `201` for nonempty successful batches |
| `PUT`    | `/teas/{tea_id}` | Update an existing tea                                |
| `DELETE` | `/teas/{tea_id}` | Delete an existing tea                                |

**Tea request example:**

```json
{ "name": "Darjeeling First Flush", "origin": "India" }
```

```bash
curl -X POST http://localhost:8000/teas \
  -H 'Content-Type: application/json' \
  -d '{"name":"Darjeeling First Flush","origin":"India"}'
```

For this branch, successful writes are performed synchronously.

## Setup and operation

```bash
python -m venv .venv
# Activate .venv for your shell
pip install -r requirements.txt
pytest -q
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for Swagger UI.

## Testing

```bash
pip install -r requirements.txt
pytest -q
```

The tests cover CRUD operations, invalid input, duplicate-name conflicts where applicable, and bulk-operation behavior. For CI specifics, inspect the branch's `Jenkinsfile`.

**Version note:** `/pulse` returns application version `1.1.0` in this branch.

## Repository files in this branch

- `.dockerignore`
- `.gitignore`
- `Dockerfile`
- `Jenkinsfile`
- `main.py`
- `requirements.txt`
- `test_main.py`

## Security and operational notes

- Do not commit production secrets, Terraform state, SSH private keys or Jenkins credential values.
- Check any committed sample credentials or configuration before using the branch outside a development environment.
- Database schema creation and deployment are branch-specific; do not assume production migrations or high availability are implemented.
- This is an educational/portfolio implementation. AWS cost, IAM scope, data persistence and runtime security require review before production use.

## What changed in this iteration

In-memory CRUD API and local Jenkins pipeline. A single FastAPI process stores teas in an in-memory list. Records are lost when the process restarts.

This is the starting point for the subsequent iterations.

## Navigation

[All branches and project evolution](https://github.com/imdoneman/python-FastAPI-backend) · [Source code for this branch](https://github.com/imdoneman/python-FastAPI-backend/tree/main)

