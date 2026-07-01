FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    TZ=Asia/Shanghai

WORKDIR /workspace

# Install system dependencies & setup timezone
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY python-fastapi/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and data folders
COPY python-fastapi/app/ ./app/
COPY investment-news/ ./investment-news/

# Pre-compile bytecode to optimize startup time
RUN python -m compileall app/

# Expose port (Railway will override this with its PORT env var)
EXPOSE $PORT

# Command to run the service in multi-worker production mode
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
