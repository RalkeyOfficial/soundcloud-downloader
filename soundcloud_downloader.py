#!/usr/bin/env python3
"""
SoundCloud HLS Downloader

This script accepts a SoundCloud track URL, resolves the HLS m3u8 stream URL,
and downloads the audio to a file (default output.mp3). It supports passing custom
tokens (client_id and OAuth token) that are necessary for accessing
protected content (like GO+ tracks).

oauth token is optional but highly encouraged, especially if you have a GO+ subscription.

Prerequisites:
- Python 3.x
- The "requests" module (install via pip if needed)
- ffmpeg installed and available on your PATH

Usage example:
    python soundcloud_downloader.py --url "https://soundcloud.com/some-user/some-track" \
        --output "song.mp3" --client_id YOUR_CLIENT_ID --oauth YOUR_OAUTH_TOKEN

Alternatively, you can supply a JSON config file (e.g., config.json) containing:
{
  "client_id": "YOUR_CLIENT_ID",
  "oauth": "YOUR_OAUTH_TOKEN",
}
and then run:
    python soundcloud_downloader.py --url "https://soundcloud.com/some-user/some-track" --config config.json

This app comes with NO guarantees that you will not get banned from SoundCloud.
"""

import requests
import argparse
import subprocess
import json
import sys
import os

"""
Check if the right packages are installed before proceeding.
(i'm not sure if its even possible to not have sys, json, etc installed, but better safe than sorry)
"""
try:
    subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
except (subprocess.SubprocessError, FileNotFoundError):
    print("ffmpeg is not installed or not in PATH. Please install it and try again.")
    sys.exit(1)


def load_config(config_path):
    """Load configuration from a JSON file."""
    if not os.path.exists(config_path):
        # Create empty config file if it doesn't exist
        with open(config_path, "w") as f:
            json.dump({"client_id": "", "oauth": ""}, f)

    with open(config_path, "r") as f:
        config = json.load(f)
    return config


def resolve_track(soundcloud_url, client_id, oauth):
    """
    Resolve the SoundCloud track URL via the SoundCloud API.
    Returns the track metadata as a JSON object.
    """
    resolve_url = "https://api-v2.soundcloud.com/resolve"
    params = {"url": soundcloud_url, "client_id": client_id}
    headers = {
        "Authorization": oauth,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }
    response = requests.get(resolve_url, params=params, headers=headers)
    response.raise_for_status()
    return response.json()


def get_hls_transcoding(track_json):
    """
    From the track JSON, choose an HLS transcoding URL.
    
    Prioritize:
      1. Transcodings with quality "hq" (the high-quality streams).
      2. Among these, only return normal HLS transcoding, not encrypted HLS.
      3. If no HQ candidate exists, fall back to any transcoding whose protocol contains "hls".
    """
    transcodings = track_json.get("media", {}).get("transcodings", [])
    
    # Filter for candidates with quality HQ and an HLS-based protocol, excluding any encrypted streams
    hq_candidates = [
        t for t in transcodings
        if t.get("quality") == "hq" 
        and "hls" in t.get("format", {}).get("protocol", "")
        and "encrypted" not in t.get("format", {}).get("protocol", "")
    ]
    
    if hq_candidates:
        # Return the first available HQ candidate
        return hq_candidates[0]["url"]
    
    # If no HQ candidates, fallback: Return any non-encrypted transcoding that supports HLS
    for transcoding in transcodings:
        protocol = transcoding.get("format", {}).get("protocol", "")
        if "hls" in protocol and "encrypted" not in protocol:
            return transcoding["url"]
    
    return None


def get_m3u8_url(transcoding_url, client_id, track_authorization, oauth):
    """
    Call the transcoding URL endpoint with the necessary client_id and tokens to obtain
    the actual m3u8 stream URL.
    """
    params = {"client_id": client_id, "track_authorization": track_authorization}
    headers = {
        "Authorization": oauth,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    }
    response = requests.get(transcoding_url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    # The API returns a JSON object with a "url" field containing the m3u8 link
    return data["url"]


def download_stream_ffmpeg(m3u8_url, output_filename, headers_str):
    """
    Invoke ffmpeg to download the HLS stream.
    The provided headers_str is sent with every segment request.

    The -c copy option tells ffmpeg to simply copy the audio stream.
    To re-encode to MP3 uncomment/change the options (e.g., "-c:a", "libmp3lame").
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-headers", headers_str,
        "-i", m3u8_url,
        # "-c", "copy",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        output_filename,
    ]
    print("Running ffmpeg command:")
    print(" ".join(cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("ffmpeg failed to process the stream.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download a SoundCloud track to MP3 using the HLS stream.")
    parser.add_argument("--url", required=True, help="SoundCloud track URL")
    parser.add_argument("--output", default="output.mp3", help="Output filename (default: output.mp3)")
    parser.add_argument("--config", default="config.json", help="Path to configuration JSON file with tokens (default: config.json)")
    parser.add_argument("--client_id", help="SoundCloud client ID")
    parser.add_argument("--oauth", help="SoundCloud OAuth token")
    args = parser.parse_args()

    client_id = args.client_id
    oauth = args.oauth

    # Load configuration tokens from a file if client_id or oauth are not provided.
    config = {}
    if not all([client_id, oauth]):
        if args.config:
            config = load_config(args.config)

    # Use command-line tokens or fall back to config file values.
    if not client_id:
        client_id = config.get("client_id")
    if not oauth:
        oauth = config.get("oauth")

    # Ensure all necessary tokens are provided.
    if not all([client_id]):
        print(
            "Error: client_id must be provided as arguments or in a config file.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        print("Resolving track information...")
        track_json = resolve_track(args.url, client_id, oauth)
        track_title = track_json.get("title", "Unknown Title")
        track_authorization = track_json.get("track_authorization", "")
        print(f"Track resolved: {track_title}")
    except Exception as e:
        print("Failed to resolve track:", e, file=sys.stderr)
        sys.exit(1)

    # Look for the HLS transcoding URL in the track metadata.
    transcoding_url = get_hls_transcoding(track_json)
    if not transcoding_url:
        print("No HLS transcoding found for this track.", file=sys.stderr)
        sys.exit(1)

    try:
        print("Fetching m3u8 URL using provided tokens...")
        m3u8_url = get_m3u8_url(transcoding_url, client_id, track_authorization, oauth)
        print("m3u8 URL obtained.")
    except Exception as e:
        print("Failed to retrieve m3u8 URL:", e, file=sys.stderr)
        sys.exit(1)

    # Prepare HTTP headers to pass to ffmpeg.
    # These headers are required to mimic a browser request, similar to the curl commands.
    ffmpeg_headers = (
        "Accept: */*\r\n"
        "Accept-Language: en-US,en;q=0.9,nl-NL;q=0.8,nl;q=0.7\r\n"
        "Cache-Control: no-cache\r\n"
        "DNT: 1\r\n"
        "Origin: https://soundcloud.com\r\n"
        "Referer: https://soundcloud.com/\r\n"
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36\r\n"
        f"Authorization: {oauth}\r\n"
    )

    print("Starting download of stream via ffmpeg...")
    download_stream_ffmpeg(m3u8_url, args.output, ffmpeg_headers)
    print("Download completed and saved to", args.output)


if __name__ == "__main__":
    main()
