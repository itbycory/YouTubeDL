from flask import Flask, request, send_file, jsonify, render_template, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import yt_dlp
import os
import logging
import json
import time
import uuid
import zipfile
import threading
from pathlib import Path
from urllib.parse import urlparse, parse_qs

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# ── Config from environment ───────────────────────────────────────────────────
DOWNLOADS_DIR = Path(os.getenv('DOWNLOADS_DIR', '/app/downloads'))
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
PORT = int(os.getenv('PORT', '8080'))
DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
DEFAULT_AUDIO_QUALITY = os.getenv('DEFAULT_AUDIO_QUALITY', '192')

# ── Rate limiting ─────────────────────────────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per hour", "20 per minute"],
    storage_uri="memory://",
)

# ── Progress store: download_id → state dict ──────────────────────────────────
_progress: dict = {}
_progress_lock = threading.Lock()

# ── Constants ─────────────────────────────────────────────────────────────────
ALLOWED_DOMAINS = {
    'youtube.com', 'www.youtube.com', 'youtu.be',
    'm.youtube.com', 'music.youtube.com',
}
ALLOWED_VIDEO_FORMATS = {'mp4', 'webm'}
ALLOWED_AUDIO_FORMATS = {'mp3', 'm4a'}
ALLOWED_AUDIO_QUALITIES = {'128', '192', '320'}


# ── Helpers ───────────────────────────────────────────────────────────────────

def validate_youtube_url(url):
    """Returns (True, None) if valid, (False, message) otherwise."""
    if not url or not isinstance(url, str):
        return False, 'URL is required'
    if len(url) > 2048:
        return False, 'URL is too long'
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            return False, 'URL must use http or https'
        if parsed.netloc.lower() not in ALLOWED_DOMAINS:
            return False, 'Only YouTube URLs are supported (youtube.com or youtu.be)'
    except Exception:
        return False, 'Invalid URL format'
    return True, None


def is_playlist_only_url(url):
    """True when the URL points to a playlist page, not a single video."""
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        return 'list' in qs and 'v' not in qs
    except Exception:
        return False


def sanitize_filename(title):
    safe = ''.join(c for c in (title or '') if c.isalnum() or c in (' ', '-', '_')).strip()
    return safe or 'download'


def best_thumbnail(info):
    for candidate in [
        info.get('thumbnail'),
        (info.get('thumbnails') or [{}])[0].get('url') if info.get('thumbnails') else None,
    ]:
        if candidate and isinstance(candidate, str):
            return candidate
    vid_id = info.get('id')
    if vid_id:
        return f'https://i.ytimg.com/vi/{vid_id}/maxresdefault.jpg'
    return None


def get_ydl_opts(base_opts=None):
    opts = {
        'quiet': True,
        'no_warnings': True,
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
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
    }
    if base_opts:
        opts.update(base_opts)
    return opts


def categorise_ydl_error(err_str):
    """Map a yt-dlp error string to a user-friendly message."""
    if '403' in err_str or 'Forbidden' in err_str:
        return 'YouTube denied the request. The video may be restricted or yt-dlp needs updating.'
    if 'Private video' in err_str:
        return 'This video is private.'
    if 'not available' in err_str.lower():
        return 'Video not available in your region or has been removed.'
    if 'Sign in' in err_str or 'login' in err_str.lower():
        return 'This video requires a YouTube account to access.'
    return f'Download failed: {err_str}'


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video-info', methods=['POST'])
@limiter.limit('30 per minute')
def get_video_info():
    try:
        data = request.get_json(silent=True) or {}
        url = (data.get('url') or '').strip()

        valid, err = validate_youtube_url(url)
        if not valid:
            return jsonify({'error': err}), 400

        ydl_opts = get_ydl_opts({
            'format': 'best',
            'extract_flat': False,
            'noplaylist': True,
        })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        is_playlist = info.get('_type') == 'playlist' or is_playlist_only_url(url)
        playlist_count = info.get('playlist_count') if is_playlist else None

        # For playlists, pull metadata from the first entry
        source = info
        if is_playlist and info.get('entries'):
            entries = list(info['entries'])
            source = entries[0] if entries else info

        video_info = {
            'title': info.get('title'),
            'thumbnail': best_thumbnail(source),
            'duration': source.get('duration'),
            'channel': info.get('uploader') or source.get('uploader'),
            'view_count': source.get('view_count'),
            'is_playlist': is_playlist,
            'playlist_count': playlist_count,
            'formats': [
                {
                    'format_id': f.get('format_id'),
                    'ext': f.get('ext'),
                    'resolution': f.get('resolution'),
                    'filesize': f.get('filesize'),
                    'vcodec': f.get('vcodec'),
                    'acodec': f.get('acodec'),
                }
                for f in source.get('formats', [])
                if f.get('ext') in (ALLOWED_VIDEO_FORMATS | ALLOWED_AUDIO_FORMATS)
            ],
        }

        return jsonify(video_info)

    except yt_dlp.utils.DownloadError as e:
        logger.error('yt-dlp error fetching video info: %s', e)
        return jsonify({'error': categorise_ydl_error(str(e))}), 502
    except Exception as e:
        logger.error('Unexpected error fetching video info: %s', e, exc_info=True)
        return jsonify({'error': 'An unexpected server error occurred.'}), 500


# ── Background download worker ────────────────────────────────────────────────

def _run_download(download_id, url, download_type, requested_format, audio_quality, download_playlist):
    """Performs the download in a background thread, updating _progress throughout."""

    def update(patch):
        with _progress_lock:
            if download_id in _progress:
                _progress[download_id].update(patch)

    def progress_hook(d):
        if d['status'] == 'downloading':
            update({
                'status': 'downloading',
                'percent': d.get('_percent_str', '0%').strip(),
                'speed': d.get('_speed_str', '').strip(),
                'eta': d.get('_eta_str', '').strip(),
                'downloaded_bytes': d.get('downloaded_bytes', 0),
                'total_bytes': d.get('total_bytes') or d.get('total_bytes_estimate', 0),
            })
        elif d['status'] == 'finished':
            update({'status': 'processing', 'percent': '100%', 'speed': '', 'eta': ''})

    unique_id = uuid.uuid4().hex

    # Use a private subdir for playlists so we can glob easily afterwards
    if download_playlist:
        work_dir = DOWNLOADS_DIR / download_id
        work_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(work_dir / '%(playlist_index)02d - %(title)s.%(ext)s')
    else:
        work_dir = None
        output_template = str(DOWNLOADS_DIR / f'%(title)s_{unique_id}.%(ext)s')

    base_opts = {
        'outtmpl': output_template,
        'progress_hooks': [progress_hook],
        'noplaylist': not download_playlist,
    }

    if download_type == 'video':
        base_opts.update({
            'format': (
                f'bestvideo[ext={requested_format}]+bestaudio'
                f'/best[ext={requested_format}]/best'
            ),
            'merge_output_format': requested_format,
        })
    else:  # audio
        quality = audio_quality if audio_quality in ALLOWED_AUDIO_QUALITIES else DEFAULT_AUDIO_QUALITY
        base_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': requested_format,
                'preferredquality': quality,
            }],
        })

    ydl_opts = get_ydl_opts(base_opts)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        if download_playlist and work_dir:
            # Collect all converted files and zip them
            glob_ext = requested_format
            files = sorted(work_dir.glob(f'*.{glob_ext}'))
            if not files:
                # Fallback: grab anything in the dir
                files = [f for f in work_dir.iterdir() if f.is_file()]

            if not files:
                update({'status': 'error', 'error': 'No files were downloaded from the playlist.'})
                return

            zip_path = DOWNLOADS_DIR / f'playlist_{unique_id}.zip'
            with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                for fp in files:
                    zf.write(fp, fp.name)
                    fp.unlink(missing_ok=True)

            # Clean up the work dir
            try:
                work_dir.rmdir()
            except Exception:
                pass

            playlist_title = sanitize_filename(info.get('title', 'playlist'))
            update({
                'status': 'done',
                'filepath': str(zip_path),
                'filename': f'{playlist_title}.zip',
                'mimetype': 'application/zip',
            })

        else:
            # Single video
            fp = Path(ydl.prepare_filename(info))
            if download_type == 'audio':
                fp = fp.with_suffix(f'.{requested_format}')

            mimetype = {
                'mp3': 'audio/mpeg',
                'm4a': 'audio/mp4',
                'mp4': 'video/mp4',
                'webm': 'video/webm',
            }.get(requested_format, f'video/{requested_format}')

            update({
                'status': 'done',
                'filepath': str(fp),
                'filename': f'{sanitize_filename(info.get("title", "download"))}.{requested_format}',
                'mimetype': mimetype,
            })

    except yt_dlp.utils.DownloadError as e:
        logger.error('Download error [%s]: %s', download_id, e)
        update({'status': 'error', 'error': categorise_ydl_error(str(e))})
    except Exception as e:
        logger.error('Unexpected download error [%s]: %s', download_id, e, exc_info=True)
        update({'status': 'error', 'error': 'An unexpected server error occurred during download.'})


# ── Download endpoints ────────────────────────────────────────────────────────

@app.route('/download', methods=['POST'])
@limiter.limit('10 per minute')
def download():
    url = (request.form.get('url') or '').strip()
    download_type = request.form.get('download_type', 'video')
    requested_format = request.form.get('format', 'mp4')
    audio_quality = request.form.get('audio_quality', DEFAULT_AUDIO_QUALITY)
    download_playlist = request.form.get('download_playlist') == 'true'

    valid, err = validate_youtube_url(url)
    if not valid:
        return jsonify({'error': err}), 400

    if download_type not in ('video', 'audio'):
        return jsonify({'error': 'Invalid download type'}), 400
    if download_type == 'video' and requested_format not in ALLOWED_VIDEO_FORMATS:
        return jsonify({'error': 'Invalid video format'}), 400
    if download_type == 'audio' and requested_format not in ALLOWED_AUDIO_FORMATS:
        return jsonify({'error': 'Invalid audio format'}), 400

    download_id = uuid.uuid4().hex
    with _progress_lock:
        _progress[download_id] = {
            'status': 'pending',
            'percent': '0%',
            'speed': '',
            'eta': '',
            'error': None,
            'filepath': None,
            'filename': None,
            'mimetype': None,
        }

    thread = threading.Thread(
        target=_run_download,
        args=(download_id, url, download_type, requested_format, audio_quality, download_playlist),
        daemon=True,
    )
    thread.start()
    logger.info('Started download [%s] url=%s type=%s fmt=%s playlist=%s',
                download_id, url, download_type, requested_format, download_playlist)

    return jsonify({'download_id': download_id})


@app.route('/progress/<download_id>')
def progress(download_id):
    with _progress_lock:
        exists = download_id in _progress
    if not exists:
        return jsonify({'error': 'Unknown download ID'}), 404

    def generate():
        while True:
            with _progress_lock:
                state = dict(_progress.get(download_id, {}))
            # Don't send filepath/mimetype to the client
            safe_state = {k: v for k, v in state.items() if k not in ('filepath', 'mimetype')}
            yield f'data: {json.dumps(safe_state)}\n\n'
            if state.get('status') in ('done', 'error'):
                break
            time.sleep(0.5)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


@app.route('/get-file/<download_id>')
def get_file(download_id):
    with _progress_lock:
        state = dict(_progress.get(download_id, {}))

    if not state:
        return jsonify({'error': 'Unknown download ID'}), 404
    if state['status'] == 'error':
        return jsonify({'error': state.get('error', 'Download failed')}), 500
    if state['status'] != 'done':
        return jsonify({'error': 'Download not complete yet'}), 202

    filepath = Path(state['filepath'])
    if not filepath.exists():
        return jsonify({'error': 'File not found — it may have already been downloaded'}), 404

    response = send_file(
        filepath,
        as_attachment=True,
        download_name=state['filename'],
        mimetype=state['mimetype'],
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'none'"

    @response.call_on_close
    def cleanup():
        try:
            filepath.unlink(missing_ok=True)
        except Exception as e:
            logger.warning('Could not delete temp file %s: %s', filepath, e)
        with _progress_lock:
            _progress.pop(download_id, None)

    return response


@app.route('/history')
def history():
    """Returns a list of all tracked downloads (excludes internal file paths)."""
    with _progress_lock:
        items = [
            {'id': k, **{kk: vv for kk, vv in v.items() if kk not in ('filepath', 'mimetype')}}
            for k, v in _progress.items()
        ]
    return jsonify(items)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)
