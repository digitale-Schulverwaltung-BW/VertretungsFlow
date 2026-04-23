FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    libldap2-dev \
    libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements*.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user and uploads directory
RUN groupadd --gid 1000 appuser && useradd --uid 1000 --gid 1000 --create-home appuser
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app

# Application code (owned by appuser)
COPY --chown=appuser:appuser . .

# Run as non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
