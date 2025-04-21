import requests
import os
import asyncio
from lib.vorbis import make_picture_block

user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


def resolve_track(soundcloud_url, client_id, oauth):
    """
    Resolve the SoundCloud track URL via the SoundCloud API.
    Returns the track metadata as a JSON object.
    """
    params = {"url": soundcloud_url, "client_id": client_id}
    headers = {
        "Authorization": oauth,
        "User-Agent": user_agent,
    }

    response = requests.get("https://api-v2.soundcloud.com/resolve", params=params, headers=headers)

    response.raise_for_status()
    
    json_data = response.json()
    if "title" not in json_data or "duration" not in json_data:
        raise ValueError("Track data is missing required fields (title and/or duration)")

    return json_data


def get_account_info(client_id, oauth):
    """
    Get the account information of the client_id and oauth.
    If oauth is not provided, or invalid, it will return an error.
    """
    params = {"client_id": client_id}
    headers = {
        "Authorization": oauth,
        "User-Agent": user_agent,
    }

    response = requests.get("https://api-v2.soundcloud.com/me", params=params, headers=headers)
    response.raise_for_status()
    return response.json()



def get_hls_transcoding(track_json, codec=None):
    """
    From the track JSON, choose an HLS transcoding URL.
    
    Prioritize:
      1. High quality streams with matching codec (if specified)
      2. Any high quality stream regardless of codec
      3. Lower quality stream with matching codec (if specified) 
      4. First available valid transcoding
      
    Only return normal HLS transcoding, not encrypted HLS.
    Exclude any transcodings with preset "abr_sq".
    """
    transcodings = track_json.get("media", {}).get("transcodings", [])
    
    # Filter out encrypted streams and abr_sq preset
    valid_transcodings = [
        t for t in transcodings
        if "encrypted" not in t.get("format", {}).get("protocol", "")
        and "hls" in t.get("format", {}).get("protocol", "")
        and t.get("preset") != "abr_sq"
    ]

    # First try to find high quality with matching codec
    if codec:
        hq_codec_matches = [
            t for t in valid_transcodings
            if t.get("quality") == "hq" and codec in t.get("preset", "")
        ]
        if hq_codec_matches:
            return hq_codec_matches[0]

    # Then look for any high quality stream
    hq_candidates = [
        t for t in valid_transcodings
        if t.get("quality") == "hq"
    ]
    if hq_candidates:
        return hq_candidates[0]

    # Then try lower quality matching codec
    if codec:
        codec_matches = [
            t for t in valid_transcodings
            if codec in t.get("preset", "")
        ]
        if codec_matches:
            return codec_matches[0]
    
    # Final fallback: first valid transcoding
    return valid_transcodings[0] if valid_transcodings else None


def get_m3u8_url(transcoding_url, track_json, client_id, oauth):
    """
    Call the transcoding URL endpoint with the necessary client_id and tokens to obtain
    the actual m3u8 stream URL.
    """
    params = {"client_id": client_id, "track_authorization": track_json["track_authorization"]}
    headers = {
        "Authorization": oauth,
        "User-Agent": user_agent,
    }
    response = requests.get(transcoding_url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    # The API returns a JSON object with a "url" field containing the m3u8 link
    return data["url"]


async def download_stream_ffmpeg(url, output_filename, output_path, codec, track_json, oauth):
    """
    Invoke ffmpeg to download the HLS stream.
    The provided headers_str is sent with every segment request.

    The -c copy option tells ffmpeg to simply copy the audio stream.
    To re-encode to MP3 uncomment/change the options (e.g., "-c:a", "libmp3lame").
    """

    # Shared headers
    ffmpeg_headers = (
        "Accept: */*\r\n"
        "Accept-Language: en-US,en;q=0.9,nl-NL;q=0.8,nl;q=0.7\r\n"
        "Cache-Control: no-cache\r\n"
        "DNT: 1\r\n"
        "Origin: https://soundcloud.com\r\n"
        "Referer: https://soundcloud.com/\r\n"
        f"User-Agent: {user_agent}\r\n"
        f"Authorization: {oauth}\r\n"
    )

    # Base FFmpeg args
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-headers", ffmpeg_headers,
    ]

    # Some codecs (e.g. opus/vorbis) need extra “security” flags
    if codec == "opus" or codec == "vorbis":
        cmd += [
            "-extension_picky", "0",
            "-allowed_extensions", "m3u8,m3u,opus,ogg",
            "-protocol_whitelist", "file,http,https,tcp,tls",
        ]

    # Always pull in the audio HLS stream
    cmd += ["-i", url]

    # Now cover‐art/metadata:
    if codec in ("mp3", "aac", "m4a"):
        # MP3/MP4‐style embedding: attach image as a second input
        cmd += ["-i", track_json["artwork_url"], "-c:v", "copy"]
        # map audio from #0, image from #1
        cmd += ["-map", "0:a", "-map", "1:v"]
        # tag it
        cmd += [
            "-metadata:s:v", "title=Album cover",
            "-metadata:s:v", "comment=Cover (front)",
            "-disposition:v:0", "attached_pic",
        ]
    elif codec in ("opus", "vorbis", "flac"):
        # Vorbis‐comment style: build in‑memory picture block
        picture_b64 = make_picture_block(track_json["artwork_url"])
        cmd += [
            "-metadata:s:a", f"METADATA_BLOCK_PICTURE={picture_b64}"
        ]
    # WAV doesn't support cover art natively, so nothing to do there

    # Finally, codec‐specific audio switches:
    if codec == "mp3":
        cmd += ["-c:a", "libmp3lame", "-b:a", "192k"]
    elif codec == "opus":
        cmd += ["-c:a", "libopus", "-b:a", "96k"]
    elif codec == "vorbis":
        cmd += ["-c:a", "libvorbis", "-qscale:a", "3"]
    elif codec == "aac":
        cmd += ["-c:a", "aac", "-b:a", "192k"]
    elif codec == "flac":
        cmd += ["-c:a", "flac", "-compression_level", "8"]
    elif codec == "wav":
        cmd += ["-c:a", "pcm_s16le"]

    # Progress/reporting
    cmd += ["-progress", "pipe:1", "-nostats"]

    # set output path & filename
    ext = {
        "mp3": "mp3",
        "opus": "ogg",
        "vorbis": "ogg",
        "aac": "m4a",
        "flac": "flac",
        "wav": "wav",
    }[codec]
    cmd.append(f"{output_path}/{output_filename}.{ext}")

    # Create output directory if it doesn't exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # spawn ffmpeg under asyncio
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    assert proc.stdout and proc.stderr

    if proc.stdout is None:
        raise RuntimeError("Failed to capture ffmpeg stdout")

    # stream progress lines
    while True:
        raw = await proc.stdout.readline()
        if not raw:
            break
        line = raw.decode().strip()
        if line.startswith("out_time_ms="):
            try:
                yield int(line.split("=", 1)[1])
            except ValueError:
                pass

    code = await proc.wait()
    if code != 0:
        err = (await proc.stderr.read()).decode()
        raise RuntimeError(f"ffmpeg exited with {code}:\n{err}")
