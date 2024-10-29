from flask import Flask, request, send_file, jsonify, render_template
import subprocess
import os
import time
import logging
from pathlib import Path

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure download directory
DOWNLOADS_DIR = Path("/app/downloads")
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    download_type = request.form['download_type']
    quality = request.form['quality']

    output_file = os.path.join(DOWNLOADS_DIR, '%(title)s.%(ext)s')

    try:
        if download_type == 'audio':
            logger.info(f"Starting audio download for URL: {url}")
            command = [
                'yt-dlp',
                '--format', 'bestaudio/best',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--output', output_file,
                url
            ]
        else:  # Video download
            logger.info(f"Starting video download for URL: {url} with quality {quality}")
            command = [
                'yt-dlp',
                '--format', quality,  # User-selected quality
                '--output', output_file,
                url
            ]

        # Run the yt-dlp command and capture the output
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Monitor the download progress
        for line in iter(process.stdout.readline, b''):
            logger.info(line.decode().strip())  # Print to console or handle progress

        process.stdout.close()
        process.wait()

        # Check if the download was successful
        if process.returncode == 0:
            logger.info("Download completed successfully.")
            # Find the downloaded file
            downloaded_file = next(DOWNLOADS_DIR.glob('*.mp3'), None) if download_type == 'audio' else next(DOWNLOADS_DIR.glob('*.mp4'), None)
            if downloaded_file:
                logger.info(f"File available for download: {downloaded_file}")
                return send_file(
                    downloaded_file,
                    as_attachment=True,
                    download_name=os.path.basename(downloaded_file),
                    last_modified=os.path.getmtime(downloaded_file)
                )
            else:
                logger.error("Downloaded file not found after process completion.")
                return jsonify({"error": "Downloaded file not found."}), 404
        else:
            logger.error(f"Download failed with return code: {process.returncode}")
            return jsonify({"error": "Download failed."}), 500

    except Exception as e:
        logger.error(f"Error during download: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
