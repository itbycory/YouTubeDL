FROM python:3.11-slim

# Install system dependencies including cron
RUN apt-get update && apt-get install -y \
    ffmpeg \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Update yt-dlp on container build
RUN pip install --upgrade yt-dlp

# Copy application files
COPY . .

# Create downloads directory
RUN mkdir -p downloads && chmod 777 downloads

# Create log directory for cron logs
RUN mkdir -p /var/log

# Create entrypoint script
RUN echo '#!/bin/bash\n\
echo "Updating yt-dlp on startup..."\n\
pip install --upgrade yt-dlp\n\
\n\
# Start cron\n\
cron\n\
\n\
# Add hourly cron job for yt-dlp updates\n\
echo "0 * * * * pip install --upgrade yt-dlp >> /var/log/ytdlp-update.log 2>&1" | crontab -\n\
\n\
# Start the Flask application\n\
exec python app.py' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Expose ports for Flask and WebSocket
EXPOSE 8080 8081

# Use entrypoint script
CMD ["/app/entrypoint.sh"]
