from flask import Flask, request, send_file, jsonify, render_template, Response
import yt_dlp
import os
import logging
from pathlib import Path
import json
import time

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

def generate_progress(d):
    if d['status'] == 'downloading':
        percent = d['_percent_str']
        speed = d['_speed_str']
        eta = d['_eta_str']
        progress_data = {
            'percent': percent,
            'speed': speed,
            'eta': eta
        }
        yield f"data: {json.dumps(progress_data)}\n\n"

@app.route('/download', methods=['POST'])
def download():
    url = request.form['url']
    download_type = request.form['download_type']
    requested_format = request.form['format']

    # Generate a unique identifier for this download
    unique_id = int(time.time() * 1000)
    output_file = DOWNLOADS_DIR / f'%(title)s_{unique_id}.%(ext)s'

    ydl_opts = {
        'outtmpl': str(output_file),
        'progress_hooks': [generate_progress],
    }

    if download_type == 'video':
        # For videos, always get the best quality
        ydl_opts.update({
            'format': 'bestvideo[ext=' + requested_format + ']+bestaudio/best[ext=' + requested_format + ']',
            'merge_output_format': requested_format,
        })
    else:  # audio
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': requested_format,
                'preferredquality': '192',
            }],
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        filename = ydl.prepare_filename(info)
        file_path = Path(filename)

        # Handle audio file extension
        if download_type == 'audio':
            file_path = file_path.with_suffix(f'.{requested_format}')

        response = send_file(
            file_path,
            as_attachment=True,
            download_name=file_path.stem.rsplit('_', 1)[0] + file_path.suffix,
            mimetype='audio/mpeg' if download_type == 'audio' else f'video/{requested_format}'
        )

        # Remove the file after sending
        file_path.unlink(missing_ok=True)

        return response

    except Exception as e:
        logger.error(f"Error during download: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/progress')
def progress():
    def generate():
        for progress in generate_progress({'status': 'downloading', '_percent_str': '0%', '_speed_str': '0 KiB/s', '_eta_str': 'Unknown'}):
            yield progress

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
