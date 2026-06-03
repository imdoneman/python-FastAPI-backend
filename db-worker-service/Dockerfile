# Use the official, lightweight Python image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies required for compiling PostgreSQL drivers
RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN adduser --disabled-password --gecos "" workeruser

WORKDIR /app

# CACHE LAYER: Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application logic
COPY . .

# Transfer ownership of the files to our non-root user
RUN chown -R workeruser:workeruser /app
USER workeruser

# Expose the internal port for the API to fetch GET requests
EXPOSE 8080

# Boot the dual-purpose worker script (handles RabbitMQ and the internal web server)
CMD ["uvicorn", "worker:app", "--host", "0.0.0.0", "--port", "8080"]