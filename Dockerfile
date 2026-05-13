# --- STAGE 1: Builder & Tester ---
# We use 'slim' to get the necessary build tools while keeping it relatively small.
FROM python:3.12-alpine AS builder

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code and tests
COPY . .

# THE GATEKEEPER: Run pytest during the build process
# If any test in test_app.py fails, the build will stop here, and no image will be created.
RUN pytest test_main.py

# --- STAGE 2: Final Production Runner ---
# We switch to 'alpine' for the smallest possible security footprint.
FROM python:3.12-alpine

WORKDIR /app

# Copy only the installed site-packages from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
# Copy only the application file needed for production
COPY main.py .

# Expose the port FastAPI will run on
EXPOSE 8000

# Run the app using Uvicorn for production-grade performance
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]