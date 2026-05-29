# =====================================================================
# STAGE 1: BUILDER & TESTING ENVIRONMENT
# =====================================================================
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install compilation toolset required for compiling C-extensions on Alpine
RUN apk update && apk add --no-cache \
    build-base \
    postgresql-dev \
    gcc \
    musl-dev

COPY requirements.txt .

# Install dependencies globally into Alpine's standard site-packages layout
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and test suites
COPY . .

# 🔥 Embedded CI/CD Gate: Execute tests. 
# If tests fail, the build halts immediately, preventing broken code from becoming an image.
RUN python -m pytest

# =====================================================================
# STAGE 2: LEAN RUNTIME ENVIRONMENT
# =====================================================================
FROM python:3.11-alpine AS runner

WORKDIR /app

# Install ONLY the runtime dynamic library needed by the postgres driver (libpq)
RUN apk update && apk add --no-cache libpq

# Copy pre-compiled Python packages directly from the builder's global site-packages
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

EXPOSE 8000

# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# 💡 FIX: Explicitly enforce an empty string root-path to anchor system routes
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--root-path", ""]