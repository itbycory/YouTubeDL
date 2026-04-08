FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    cron \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Install Python packages (cached layer — copy requirements before source)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pin yt-dlp to the version resolved from requirements.txt;
# upgrade only happens at runtime via entrypoint.sh
RUN pip install --no-cache-dir --upgrade yt-dlp

# Copy application files
COPY . .

# Create downloads and log directories with correct ownership
RUN mkdir -p downloads logs \
    && chown -R appuser:appuser /app

# Drop to non-root user
USER appuser

# Expose Flask port
EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]
