FROM python:3.12-slim

WORKDIR /app

# System deps for extractors
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget \
    libxml2-dev libxslt-dev \
    libssl-dev libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (only if playwright is enabled)
RUN python -m playwright install chromium --with-deps 2>/dev/null || true

COPY app/ ./app/

CMD ["python", "-m", "app.workers.collect"]
