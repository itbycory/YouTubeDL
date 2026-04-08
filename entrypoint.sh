#!/bin/bash
set -e

echo "Updating yt-dlp on startup..."
pip install --quiet --upgrade yt-dlp

# Add hourly cron job (runs as appuser via cron — requires cron daemon)
echo "0 * * * * pip install --quiet --upgrade yt-dlp >> /app/logs/ytdlp-update.log 2>&1" | crontab -

# Start cron in background
cron

echo "Starting Flask application on port ${PORT:-8080}..."
exec python app.py
