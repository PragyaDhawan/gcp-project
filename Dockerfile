# Dockerfile (replace your current Dockerfile)
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install system certs, openssl and build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      libssl-dev \
      ca-certificates \
      pkg-config \
      curl \
      openssl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r requirements.txt \
 && python -m pip install --upgrade certifi

# Copy app code
COPY . .

ENV PORT=8080
EXPOSE 8080

# Run using gunicorn + uvicorn worker
CMD ["sh", "-c", "exec gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b :$PORT --timeout 120 main:app"]