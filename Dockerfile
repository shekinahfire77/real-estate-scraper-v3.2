# Multi-stage build for production-ready image
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1000 scraper && \
    mkdir -p /app/data /app/logs && \
    chown -R scraper:scraper /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/scraper/.local

# Copy application code
COPY --chown=scraper:scraper . .

# Switch to non-root user
USER scraper

# Add user's local bin to PATH
ENV PATH=/home/scraper/.local/bin:$PATH

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Create volume mount points
VOLUME ["/app/data", "/app/logs"]

# Default command
CMD ["python", "-m", "src.main_with_db"]
