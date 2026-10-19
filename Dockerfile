FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

# Install system dependencies & Node.js 20
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    git \
    build-essential \
    libpq-dev \
    ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Node dependencies & Playwright Chromium
COPY package.json /app/
RUN npm install --omit=dev \
    && npx playwright install --with-deps chromium || true

# Copy application source
COPY . /app/

# Expose server port
EXPOSE 8000

# Start FastAPI production server with Uvicorn
CMD exec uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}
