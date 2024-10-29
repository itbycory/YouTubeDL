YouTube Downloader

This project is a simple web-based YouTube downloader built using Flask and yt-dlp, a command-line tool that downloads media from YouTube and other video sites. This app allows users to download audio and video in various formats, providing an easy-to-use interface.

Features
Download videos or audio-only from YouTube
Select preferred quality for video downloads
Automatically convert audio to MP3 format
Prerequisites
Docker installed on your machine
A Personal Access Token (PAT) if cloning the repository from GitHub
Installation and Setup
1. Clone the Repository
Use the following command to clone this repository:

bash
Copy code
git clone https://github.com/your-username/YouTubeDownloader.git
cd YouTubeDownloader
2. Build and Run the Docker Container
Build the Docker image and run the container as follows:

bash
Copy code
# Build the Docker image
docker build -t youtube-downloader .

# Run the Docker container
docker run -d -p 8080:8080 --name yt-downloader youtube-downloader
This will start the app in a Docker container, accessible on http://localhost:8080.

3. Access the Application
Open your browser and go to http://localhost:8080 to use the YouTube Downloader web interface.

Usage
Paste the YouTube URL of the video you want to download.
Select the download type: Video or Audio.
Choose the desired quality (for video).
Click Download to start the download process.
Project Structure
bash
Copy code
.
├── app.py                  # Main Flask application file
├── Dockerfile              # Docker configuration for building the app
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html          # HTML template for the web interface
└── downloads/              # Directory to store downloaded files
Configuration
The downloads directory in the container is /app/downloads.
Modify app.py to change settings like file retention policies or logging.
Docker Commands
To stop the container:

bash
Copy code
docker stop yt-downloader
To remove the container:

bash
Copy code
docker rm yt-downloader
To remove the image:

bash
Copy code
docker rmi youtube-downloader
License
This project is licensed under the MIT License.
