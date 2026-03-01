# Use official Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy dependency file first (for caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# use env default PORT for local testing (App Engine will set this)
ENV PORT=8080

# Expose port
EXPOSE 8000

# # Run FastAPI app
# # CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# # Run FastAPI app with Gunicorn managing Uvicorn workers
# CMD ["gunicorn", "main:app", "--workers", "10", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]

# run gunicorn and let $PORT be expanded by the shell
# -k uvicorn.workers.UvicornWorker for FastAPI/ASGI
# reduce workers to 2 to avoid OOM on small instances
CMD ["sh", "-c", "exec gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b :$PORT --timeout 120 main:app"]