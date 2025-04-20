# SoundCloud HLS Downloader

A super simple Python command-line tool for downloading audio tracks from SoundCloud using HLS (HTTP Live Streaming) protocol. This tool supports both regular and GO+ tracks when provided with appropriate authentication tokens.

## Features

- Download any accessible content in different formats
- Full support for both regular and GO+ premium tracks
- Token-based authentication
- Multiple audio codec options
- Customizable output file naming

## Prerequisites

- Python 3.x or newer
- FFmpeg installed and available in your system PATH
- Required Python packages:
  - `requests`, `textual`, `rich`

## Installation

### Quick Setup

1. Clone this repository:
   ```bash
   git clone https://github.com/RalkeyOfficial/soundcloud-downloader.git
   cd soundcloud-downloader
   ```

2. Install the required Python package:
   ```bash
   pip install -r requirements.txt
   ```

3. Install FFmpeg:
   - **Windows**:
     - Using winget (recommended): `winget install ffmpeg`
     - Using chocolatey: `choco install ffmpeg`
     - Alternatively: Download from [FFmpeg official website](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg` or equivalent for your distribution

### Verifying Installation

Verify FFmpeg is correctly installed:
```bash
ffmpeg -version
```

## Configuration

There are two ways to provide the required authentication tokens:

### 1. Using a Configuration File (Recommended)

Create a `config.json` file in the same directory as the script:

```json
{
	"client_id": "YOUR_CLIENT_ID",
	"oauth": "YOUR_OAUTH_TOKEN" // optional
}
```

### 2. Using Command Line Arguments

Provide tokens directly when running the script (see Usage section below).

## Usage

### Basic Usage

```bash
# With config.json in place
python soundcloud_downloader.py --url "https://soundcloud.com/artist/track-name" --output "song_name"
```

### Advanced Usage

```bash
python soundcloud_downloader.py \
    --url "https://soundcloud.com/artist/track-name" \
    --output "song_name" \
    --codec "vorbis" \
    --client_id YOUR_CLIENT_ID \
    --oauth YOUR_OAUTH_TOKEN
```

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--url` | (Required) SoundCloud track URL | None |
| `--output` | Output filename (excluding extension) | output |
| `--codec` | Audio codec (mp3, opus, vorbis, aac, flac, wav) | mp3 |
| `--config` | Path to configuration JSON file | config.json |
| `--client_id` | SoundCloud client ID | From config |
| `--oauth` | SoundCloud OAuth token | From config |

The SoundCloud OAuth token is only required for GO+ tracks, and can be entirely omitted for other tracks.
A OAuth token looks like this:
```
// obviously not a real token
OAuth 1-234567-123456789-aBcD1234eFgHIj
```

### Codec Quality Notes

- **MP3**: 192 Kbps (higher bitrate, standard compatibility)
- **Opus**: 96 Kbps (excellent quality, lower compatibility)
- **Vorbis**: 96 Kbps (excellent quality, lower compatibility)
- **AAC**: 192 Kbps (Not recommended unless you need it)
- **Flac**: Compression level: 8 (Not recommended unless you need it)
- **Wav**: 16-bit PCM (Not recommended unless you need it)

Opus and Vorbis codecs provide similar perceived quality to MP3 at half the bitrate, resulting in smaller file sizes.

## Troubleshooting

The script will exit with appropriate error messages if:

- FFmpeg is not installed or not found in PATH
- Required tokens are missing
- Track URL cannot be resolved
- HLS stream is not available for the track
- Download process fails

## Important Notes

- This tool **requires** valid SoundCloud authentication tokens
- For GO+ tracks, you need tokens from a GO+ subscription account
- No guarantee is provided regarding account safety - use at your own risk

## Legal Disclaimer

This tool is for educational purposes only. Make sure to comply with SoundCloud's terms of service and respect copyright laws when using this tool. Only download content you have permission to access.
