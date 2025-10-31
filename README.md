# YouTube Downloader

A Flask-based web application that allows users to download YouTube videos and audio using yt-dlp. The application provides a simple web interface for downloading content in various formats and qualities.

## Features

- Download YouTube videos in multiple quality options (1080p, 720p, 480p)
- Extract audio from videos (MP3 format)
- Simple and intuitive web interface
- Docker support for easy deployment
- Progress tracking during downloads

## Prerequisites

- Docker and Docker Compose
- Python 3.11+ (if running without Docker)
- FFmpeg (required for audio extraction)

## Project Structure

```
YouTubeDL-main/
├── app.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── downloads/
└── templates/
    └── index.html
```

## Installation

### Using Docker (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/itbycory/YouTubeDL.git
cd YouTubeDL
```

2. Build and run the Docker container:
```bash
docker compose up -d
```

The application will be available at `http://localhost:8080`

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/itbycory/YouTubeDL.git
cd YouTubeDL
```

2. Install FFmpeg:
- For Ubuntu/Debian:
  ```bash
  sudo apt-get update && sudo apt-get install ffmpeg
  ```
- For macOS:
  ```bash
  brew install ffmpeg
  ```
- For Windows:
  Download from [FFmpeg official website](https://ffmpeg.org/download.html)

3. Create and activate a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. Install the required packages:
```bash
pip install -r requirements.txt
```

5. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:8080`

## Usage

1. Open your web browser and navigate to `http://localhost:8080`
2. Paste a YouTube URL into the input field
3. Select download type (video or audio)
4. If downloading video, select the desired quality
5. Click the Download button
6. Wait for the download to complete
7. The file will be automatically downloaded to your computer

## Configuration

The following environment variables can be modified in the `docker-compose.yml` file:

- `PYTHONUNBUFFERED`: Controls Python output buffering (default: 1)
- Port mapping: Can be changed from 8080 to another port if needed

## File Storage

Downloaded files are temporarily stored in the `downloads` directory. When using Docker, this directory is mounted as a volume to persist downloads between container restarts.

## Contributing

1. Fork the repository from [https://github.com/cmarcus93/YouTubeDL](https://github.com/cmarcus93/YouTubeDL)
2. Create a new branch for your feature
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## Security Considerations

- This application is intended for personal use only
- Be aware of YouTube's terms of service regarding content downloading
- The application doesn't implement rate limiting or user authentication
- Consider adding security measures before deploying in a production environment

## Known Issues

- Large files may take longer to process
- Some video formats might not be available for certain URLs
- Progress tracking might not be accurate for all downloads

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for the download functionality
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [Docker](https://www.docker.com/) for containerization

## Support

For support, please open an issue in the [GitHub repository](https://github.com/cmarcus93/YouTubeDL) or contact the maintainers.
