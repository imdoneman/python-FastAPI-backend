# Tea House Backend — `iteration-2`

> **Branch 2 of 6 · Persistent SQL CRUD API**

[Project repository](https://github.com/imdoneman/python-FastAPI-backend) · [Browse this branch](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2)

## Purpose

The API uses SQLAlchemy sessions and database-backed tea records. Docker Compose starts the API and PostgreSQL with a database health check.

The branch sequence is documented in the [project overview](https://github.com/imdoneman/python-FastAPI-backend#development-roadmap).

## Technology stack

FastAPI, SQLAlchemy, PostgreSQL 16, SQLite (test/local fallback), Docker Compose, pytest

## Architecture

```text
Client → FastAPI → SQLAlchemy → PostgreSQL
                   └────────→ SQLite (when DATABASE_URL is unset)
```

The API handles database writes synchronously. Duplicate names produce HTTP `409 Conflict`; bulk inserts reject duplicate names without partially committing the batch.
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

```bash
docker compose -f docker-compose.yaml up --build -d
curl http://localhost:8000/pulse
docker compose -f docker-compose.yaml down
```

For local tests without PostgreSQL:

```bash
pip install -r requirements.txt
pytest -q
```

`DATABASE_URL` defaults to `sqlite:///./tea_house.db`. The Compose file contains **demonstration database credentials**; replace them before any exposed deployment.


## Testing

```bash
pip install -r requirements.txt
pytest -q
```

The tests cover CRUD operations, invalid input, duplicate-name conflicts where applicable, and bulk-operation behavior. For CI specifics, inspect the branch's `Jenkinsfile`.

**Version note:** `/pulse` returns application version `2.1.0` in this branch.

## Repository files in this branch

- `.dockerignore`
- `.gitignore`
- `Dockerfile`
- `Jenkinsfile`
- `database.py`
- `docker-compose.yaml`
- `main.py`
- `models.py`
- `requirements.txt`
- `schemas.py`
- `test_main.py`

## Security and operational notes

- Do not commit production secrets, Terraform state, SSH private keys or Jenkins credential values.
- Check any committed sample credentials or configuration before using the branch outside a development environment.
- Database schema creation and deployment are branch-specific; do not assume production migrations or high availability are implemented.
- This is an educational/portfolio implementation. AWS cost, IAM scope, data persistence and runtime security require review before production use.

## What changed in this iteration

Persistent SQL CRUD API. The API uses SQLAlchemy sessions and database-backed tea records. Docker Compose starts the API and PostgreSQL with a database health check.

Compare with the preceding branch: [`main`](https://github.com/imdoneman/python-FastAPI-backend/tree/main).

## Navigation

[All branches and project evolution](https://github.com/imdoneman/python-FastAPI-backend) · [Source code for this branch](https://github.com/imdoneman/python-FastAPI-backend/tree/iteration-2)
