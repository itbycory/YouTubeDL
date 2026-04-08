# YouTube Downloader

A Flask web app for downloading YouTube videos and audio, powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Features

- Download videos as **MP4** or **WebM**
- Extract audio as **MP3** or **M4A** at 128 / 192 / 320 kbps
- **Real-time progress bar** with speed and ETA
- **Playlist support** — downloads all videos as a zip file
- Video preview with thumbnail, channel, and duration
- Rate limiting and URL validation built in
- Dark mode support
- Docker ready

## Quick start (Docker)

```bash
git clone https://github.com/itbycory/YouTubeDL.git
cd YouTubeDL
docker compose up -d
```

Open `http://localhost:8080`.

## Manual setup

Requirements: Python 3.11+, FFmpeg

```bash
git clone https://github.com/itbycory/YouTubeDL.git
cd YouTubeDL

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
python app.py
```

Open `http://localhost:8080`.

## Configuration

Copy `.env.example` to `.env` and adjust as needed. All settings can also be set as environment variables.

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | Port Flask listens on |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `DOWNLOADS_DIR` | `/app/downloads` | Temporary download directory |
| `DEFAULT_AUDIO_QUALITY` | `192` | Default audio bitrate (`128`, `192`, `320`) |
| `MAX_CONTENT_LENGTH` | `1073741824` | Max upload/response size (bytes) |

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web UI |
| `POST` | `/video-info` | Fetch video metadata (JSON body: `{"url": "..."}`) |
| `POST` | `/download` | Start a background download, returns `{"download_id": "..."}` |
| `GET` | `/progress/<id>` | Server-Sent Events stream of download progress |
| `GET` | `/get-file/<id>` | Retrieve the completed file |
| `GET` | `/history` | List all tracked downloads in this session |

## Rate limits

| Endpoint | Limit |
|---|---|
| `/video-info` | 30 requests / minute |
| `/download` | 10 requests / minute |
| All other routes | 200 / hour, 20 / minute |

## Project structure

```
YouTubeDL/
├── app.py                  # Flask application
├── templates/
│   └── index.html          # Frontend UI
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh           # Container startup script
├── requirements.txt
├── .env.example            # Environment variable reference
├── downloads/              # Temporary file storage (volume-mounted)
└── logs/                   # yt-dlp update logs (volume-mounted)
```

## Troubleshooting

**Downloads fail with a 403 error**
YouTube occasionally blocks requests. The container auto-updates yt-dlp hourly; you can also trigger it manually:
```bash
docker compose exec yt-dlp-app pip install --upgrade yt-dlp
```

**Where are the logs?**
- Application logs: `docker compose logs -f`
- yt-dlp update cron logs: `./logs/ytdlp-update.log`

**Health check failing?**
The health check uses `wget`. Ensure you are running the container from the provided Dockerfile (slim image does not include `curl`).

**Port already in use?**
Set `PORT=8081` (or any free port) in your `.env` file.

## Security notes

This application is intended for **personal use only**. It does not implement authentication. Do not expose it to the public internet without placing it behind a reverse proxy with access controls.

Please respect [YouTube's Terms of Service](https://www.youtube.com/t/terms) regarding content downloading.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [Flask](https://flask.palletsprojects.com/)
- [Tailwind CSS](https://tailwindcss.com/)
- [Docker](https://www.docker.com/)
