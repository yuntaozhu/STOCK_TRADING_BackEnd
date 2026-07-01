FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /workspace

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY python-fastapi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and data folders
COPY python-fastapi/app/ ./app/
COPY investment-news/ ./investment-news/

# Expose port (Railway will override this with its PORT env var)
EXPOSE $PORT

# Command to run the service
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
