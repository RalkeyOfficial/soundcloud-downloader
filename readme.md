# SoundCloud HLS Downloader

A super simple Python-based command-line tool for downloading audio tracks from SoundCloud using HLS (HTTP Live Streaming) protocol. This tool supports downloading both regular and GO+ tracks when provided with appropriate authentication tokens.

## Features

- Download any accessible SoundCloud track in MP3 format
- Support for both regular and GO+ tracks
- Token-based authentication support
- Configuration file support for storing credentials

## Prerequisites

- Python 3.x
- FFmpeg installed and available in your system PATH
- Required Python packages:
  - `requests`

## Installation

1. Clone this repository or download the script
2. Install the required Python package:
   ```bash
   pip install requests
   ```
3. Install FFmpeg:
   - **Windows**: 
     - Using winget (recommended): `winget install ffmpeg`
     - Alternatively: Download from [FFmpeg official website](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg` or equivalent for your distribution

## Configuration

There are two ways to provide the required authentication tokens:

### 1. Using a Configuration File (Recommended)

Create a `config.json` file in the same directory as the script:

```json
{
	"client_id": "YOUR_CLIENT_ID",
	"oauth": "YOUR_OAUTH_TOKEN"
}
```

### 2. Using Command Line Arguments

Provide tokens directly when running the script (see Usage section below).

## Usage

### Basic Usage

```bash
# assuming you have a config.json
python soundcloud_downloader.py --url "https://soundcloud.com/artist/track-name" --output "song.mp3"
```

### Advanced Usage

```bash
python soundcloud_downloader.py \
    --url "https://soundcloud.com/artist/track-name" \
    --output "song.mp3" \
    --client_id YOUR_CLIENT_ID \
    --oauth YOUR_OAUTH_TOKEN \
    --config second_account_config.json
```

### Command Line Arguments

- `--url`: (Required) SoundCloud track URL
- `--output`: Output filename (default: output.mp3)
- `--config`: Path to configuration JSON file (default: config.json)
- `--client_id`: SoundCloud client ID (optional if provided in config file)
- `--oauth`: SoundCloud OAuth token (optional if provided in config file, recommended for GO+ users)

## Important Notes

- This tool **requires** valid SoundCloud authentication token (client_id and oauth)
- For GO+ tracks, you need tokens from a GO+ subscription account and add the oauth token.
- Downloads are in 192Kbps (since 320Kbps is a little lie people tell to advertise their service).
- No guarantee is provided regarding account safety - use at your own risk

## Error Handling

The script will exit with appropriate error messages if:

- FFmpeg is not installed or not found in PATH
- Required tokens are missing
- Track URL cannot be resolved
- HLS stream is not available for the track
- Download process fails

## Legal Disclaimer

This tool is for educational purposes only. Make sure to comply with SoundCloud's terms of service and respect copyright laws when using this tool.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.
