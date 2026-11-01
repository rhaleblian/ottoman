FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates git gosu && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install Python deps separately for caching
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy daemon code
COPY daemon /app/daemon
RUN mkdir -p /app/daemon/cache
COPY entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh && chown -R appuser:appuser /app

ENTRYPOINT ["/app/entrypoint.sh"]

