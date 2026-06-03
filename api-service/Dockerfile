# Use the official, lightweight Python image
FROM python:3.11-slim

# Set environment variables to optimize Python inside Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create a non-root user for security (Kubernetes best practice)
RUN adduser --disabled-password --gecos "" apiuser

# Set the working directory
WORKDIR /app

# CACHE LAYER: Copy only the requirements first
# If requirements don't change, Docker skips reinstalling them on the next build!
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the actual application code
COPY . .

# Transfer ownership of the files to our non-root user
RUN chown -R apiuser:apiuser /app
USER apiuser

# Expose the web server port
EXPOSE 8000

# Boot the API server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]