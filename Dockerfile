
# ============================================================
# STAGE 1: BUILD AND TEST
# ============================================================
FROM python:3.11-alpine AS builder

WORKDIR /app

RUN apk add --no-cache \
    build-base \
    postgresql-dev

# Runtime dependencies go into a dedicated virtual environment.
COPY requirements.txt requirements-dev.txt ./

RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# A separate environment contains the testing dependencies.
RUN python -m venv /opt/test-venv \
    && /opt/test-venv/bin/pip install --no-cache-dir -r requirements-dev.txt

COPY . .

# A failing test prevents the image from being built.
RUN /opt/test-venv/bin/python -m pytest -v

# ============================================================
# STAGE 2: LEAN RUNTIME
# ============================================================
FROM python:3.11-alpine AS runner

WORKDIR /app

RUN apk add --no-cache libpq

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY main.py database.py models.py schemas.py ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--root-path", ""]
