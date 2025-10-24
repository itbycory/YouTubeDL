#!/bin/bash

# Update yt-dlp on startup
echo "Updating yt-dlp on startup..."
pip install --upgrade yt-dlp

# Start cron in the background
cron

# Add cron job for hourly updates
echo "0 * * * * pip install --upgrade yt-dlp >> /var/log/ytdlp-update.log 2>&1" | crontab -

# Start the Flask application
exec python app.py
