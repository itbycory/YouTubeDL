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

def get_ydl_opts(base_opts=None):
    """
    Returns yt-dlp options with anti-detection measures
    """
    opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['webpage', 'configs'],
            }
        },
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'file_access_retries': 3,
        'cookiesfrombrowser': None,  # Can be set to ('chrome',) or ('firefox',) if needed
    }
    
    if base_opts:
        opts.update(base_opts)
    
    return opts

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video-info', methods=['POST'])
def get_video_info():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400

        ydl_opts = get_ydl_opts({
            'format': 'best',
            'writesubtitles': False,
            'extract_flat': False,
        })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
        # More robust thumbnail retrieval
        def extract_best_thumbnail(info):
            # Check different possible thumbnail locations
            thumbnail_candidates = [
                info.get('thumbnail'),  # Primary thumbnail
                info.get('thumbnails', [{}])[0].get('url') if info.get('thumbnails') else None,
            ]
            
            # Return the first non-None, non-empty candidate
            for candidate in thumbnail_candidates:
                if candidate and isinstance(candidate, str):
                    return candidate
            
            # Attempt to construct YouTube thumbnail URL as a fallback
            try:
                video_id = info.get('id')
                if video_id:
                    return f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
            except Exception:
                pass
            
            return None

        video_info = {
            'title': info.get('title'),
            'thumbnail': extract_best_thumbnail(info),
            'duration': info.get('duration'),
            'channel': info.get('uploader'),
            'view_count': info.get('view_count'),
            'formats': [
                {
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'resolution': f.get('resolution'),
                    'filesize': f.get('filesize'),
                    'vcodec': f.get('vcodec'),
                    'acodec': f.get('acodec'),
                } for f in info.get('formats', []) if f.get('ext') in ['mp4', 'webm', 'mp3', 'm4a']
            ]
        }
        
        return jsonify(video_info)
    except Exception as e:
        logger.error(f"Error fetching video info: {str(e)}")
        error_msg = str(e)
        if '403' in error_msg or 'Forbidden' in error_msg:
            error_msg = "Unable to access video. Try updating yt-dlp or the video may be restricted."
        return jsonify({'error': error_msg}), 500

def generate_progress(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%')
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'Unknown')
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
    
    unique_id = int(time.time() * 1000)
    output_file = DOWNLOADS_DIR / f'%(title)s_{unique_id}.%(ext)s'
    
    base_opts = {
        'outtmpl': str(output_file),
        'progress_hooks': [generate_progress],
    }

    if download_type == 'video':
        base_opts.update({
            'format': f'bestvideo[ext={requested_format}]+bestaudio/best[ext={requested_format}]/best',
            'merge_output_format': requested_format,
        })
    else:  # audio
        base_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': requested_format,
                'preferredquality': '192',
            }],
        })

    ydl_opts = get_ydl_opts(base_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        file_path = Path(filename)
        
        if download_type == 'audio':
            file_path = file_path.with_suffix(f'.{requested_format}')
        
        original_title = info.get('title', 'download')
        # Sanitize filename to remove invalid characters
        clean_title = "".join(c for c in original_title if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_filename = f"{clean_title}.{requested_format}"
            
        response = send_file(
            file_path,
            as_attachment=True,
            download_name=clean_filename,
            mimetype='audio/mpeg' if download_type == 'audio' else f'video/{requested_format}'
        )
        
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'none'"
        
        try:
            file_path.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Could not delete temporary file: {str(e)}")
            
        return response
    except Exception as e:
        logger.error(f"Error during download: {str(e)}")
        error_msg = str(e)
        if '403' in error_msg or 'Forbidden' in error_msg:
            error_msg = "Unable to download video. YouTube may have blocked the request. Try again or update yt-dlp."
        return jsonify({'error': error_msg}), 500

@app.route('/progress')
def progress():
    def generate():
        for progress in generate_progress({'status': 'downloading', '_percent_str': '0%', '_speed_str': '0 KiB/s', '_eta_str': 'Unknown'}):
            yield progress
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
