#!/usr/bin/env python3
"""
SoundCloud HLS Downloader

A Python-based GUI application for downloading high-quality audio from SoundCloud using HLS streams.
The app provides a user-friendly interface for downloading tracks and supports various audio formats.

Key Features:
- Modern Text-based User Interface (TUI)
- Multiple audio codec support (mp3, opus, vorbis, aac, flac, wav)
- High-quality audio downloads via HLS streams
- GO+ content support with OAuth token
- Automatic artwork embedding from SoundCloud
- Progress tracking and error handling

Prerequisites:
- Python 3.x
- ffmpeg installed and available on your PATH
- Required Python packages (install via pip):
  - requests
  - textual
  - rich
  - mutagen

Authentication:
The app requires a SoundCloud client_id and supports OAuth tokens. These can be provided via config.json:
{
  "client_id": "YOUR_CLIENT_ID",
  "oauth": "YOUR_OAUTH_TOKEN"  # Optional but highly recommended
}

Note on OAuth Token:
While the OAuth token is optional, it is HIGHLY ENCOURAGED to provide one, especially if you:
- Have a GO+ subscription
- Need higher quality audio streams

Metadata & Artwork:
The app automatically:
- Downloads the track's original artwork from SoundCloud
- Embeds the artwork as cover image in the audio file
- Wav does not support artwork embedding

Usage:
Simply run the script to launch the TUI:
    python soundcloud_downloader.py

Note: Command-line interface (CLI) support is planned for future releases.

Security Note:
- Store your tokens securely in config.json
- Never share your tokens or commit them to version control
- This app comes with NO guarantees that you will not get banned from SoundCloud

Author: Ralkey
Version: 2.1.2
"""

# if this file is imported, exit
if __name__ != "__main__":
    exit()


import argparse
import subprocess
import sys
import re
import os
import asyncio
from rich.markup import escape
from textual import on
from textual.app import App, ComposeResult
from textual.color import Color
from textual.widgets import Button, Label, Input, ProgressBar, Select
from textual.containers import Container
from textual.validation import Regex, Length
from lib.soundcloud import resolve_track, get_hls_transcoding, get_m3u8_url, download_stream_ffmpeg, get_account_info
from lib.config import load_config
from lib.debounce import debounce_async
from lib.events import ProgressEvent, StageEvent
from lib.error_handler import log_error, log_info

VERSION = "2.1.2"
AUTHOR = "Ralkey"

log_info(f"Starting SoundCloud Downloader v{VERSION}")

try:
    subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
except (subprocess.SubprocessError, FileNotFoundError) as e:
    log_error(e, context={"error": "ffmpeg not found"})
    print("ffmpeg not found.")
    sys.exit(1)


# parse args
parser = argparse.ArgumentParser(description="Download a SoundCloud track to MP3 using the HLS stream.")
parser.add_argument("--url", help="SoundCloud track URL")
parser.add_argument("--config", default="config.json", help="Path to configuration JSON file with tokens (default: config.json)")
parser.add_argument("--client_id", help="SoundCloud client ID")
parser.add_argument("--oauth", help="SoundCloud OAuth token")
parser.add_argument("--output", default="output", help="Output filename (default: output)")
parser.add_argument("--codec",
                    default="mp3",
                    choices=["mp3", "opus", "vorbis", "aac", "flac", "wav"],
                    help="Audio codec to use (default: mp3)"
)
args = parser.parse_args()

# global variables
client_id = args.client_id
oauth = args.oauth
user_info = {}

# Load configuration tokens from a file if client_id or oauth are not provided.
config = {}
if not all([client_id, oauth]):
    if args.config:
        try:
            config = load_config(args.config)
        except Exception as e:
            log_error(e, context={"config_file": args.config})

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


# get user info
try:
    user_info = get_account_info(client_id, oauth)
except Exception as e:
    log_error(e, context={"error": "Failed to get user account info"})
    user_info["username"] = "Unknown"


class SoundCloudDownloaderApp(App):
    CSS_PATH = "styles/style.tcss"

    def __init__(self):
        super().__init__()
        self.track_json = {}
        self.output_path = "./output"

    def on_mount(self) -> None:
        self.screen.styles.border = ("solid", Color(255, 85, 0))

    def compose(self) -> ComposeResult:
        with Container(id="header_container"):
            yield Label("SoundCloud HLS Downloader", id="title")
            yield Label(f"v{VERSION} - By Ralkey", id="subtitle")

        yield Label(f"Logged in as {user_info['username']}", id="user_info", classes=("full_width"))

        with Container(id="content_container"):
            with Container(classes=("sub_content_container")): # this container literally just exists to help with centering and limiting the width.
                with Container(id="input_row"):
                    yield Input(type="text", placeholder="SoundCloud URL", id="url_input", validators=[
                        Regex(regex=r"^https:\/\/soundcloud\.com\/[^/]+/[^/]+$")
                    ])
                    yield Input(type="text", placeholder="File name", id="file_name_input", validators=[Length(minimum=1)])
                    yield Select(allow_blank=False, # removes the default blank option
                        options=(
                            ("mp3", "mp3"),
                            ("opus", "opus"),
                            ("vorbis", "vorbis"),
                            ("aac", "aac"),
                            ("flac", "flac"),
                            ("wav", "wav")
                        ),
                        id="codec_select")

                with Container(id="button_container"):
                    yield Button("Download", id="download_button", disabled=True, classes=("button_class"))
                    yield Button("Open folder", id="open_folder_button", classes=("button_class"))

    @on(Input.Changed, "#url_input")
    @on(Input.Changed, "#file_name_input")
    @on(Select.Changed, "#codec_select")
    def update_validation_state(self, event: Input.Changed | Select.Changed = None) -> None:
        url_input = self.query_one("#url_input")
        file_name_input = self.query_one("#file_name_input")
        codec_select = self.query_one("#codec_select")

        is_valid = (
            url_input.validate(url_input.value).is_valid and
            file_name_input.validate(file_name_input.value).is_valid and
            codec_select.value is not None
            and self.track_json is not None
        )
        
        # Update download button based on all validation states
        download_button = self.query_one("#download_button")
        download_button.disabled = not is_valid

    @on(Input.Changed, "#url_input")
    async def update_file_name(self, event: Input.Changed) -> None:
        file_name_input = self.query_one("#file_name_input")

        # reset values to prepare for new fetch
        self.track_json = {}
        file_name_input.clear()

        # update validation state
        self.update_validation_state()

        # if the URL is invalid, don't fetch the track info
        if not event.validation_result.is_valid:
            return
        
        await self.fetch_track_info(event=event)

    @debounce_async(delay_seconds=0.5)
    async def fetch_track_info(self, event):
        file_name_input = self.query_one("#file_name_input")

        try:
            self.track_json = resolve_track(event.value, client_id, oauth)
            file_name_input.clear()
            file_name_input.insert(self.track_json["title"], 0)
        except Exception as e:
            log_error(e, context={"track_url": event.value})
        finally:
            self.update_validation_state()


    @on(Button.Pressed, "#open_folder_button")
    async def open_folder(self, event: Button.Pressed) -> None:
        subprocess.run(["explorer", os.path.abspath(self.output_path)], shell=True)


    @on(Button.Pressed, "#download_button")
    async def start_download(self, event: Button.Pressed) -> None:
        input_container = self.query_one("#button_container")

        existing = input_container.query("#progress_bar_container")
        if existing:
            # There should be at most one, but just in case:
            for widget in existing:
                await widget.remove()

        # mount progress_bar_container
        await input_container.mount(Container(
                Label("", id="progress_label"),
                ProgressBar(name="download_progress", id="progress_bar"),
                id="progress_bar_container"
            ))

        progress_label = self.query_one("#progress_label")
        progress_bar = self.query_one("#progress_bar")

        # Remove invalid Windows filename characters
        file_name = re.sub(r'[<>:"/\\|?*]', '', self.query_one("#file_name_input").value)
        # Remove any leading/trailing whitespace and periods
        file_name = file_name.strip().strip('.')
        # Use CON, PRN etc. with an underscore to avoid reserved names
        if file_name.upper() in ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                                'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 
                                'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']:
            file_name = f"{file_name}_"

        codec = self.query_one("#codec_select").value
        transcoding = {}
        m3u8_url = None

        # Get the highest quality HLS transcoding URL
        try:
            progress_label.update("Getting HLS transcoding URL...")
            transcoding = get_hls_transcoding(self.track_json, codec)
            progress_label.update("HLS transcoding URL resolved.")
        except Exception as e:
            error_msg = "No HLS transcoding found for this track"
            log_error(e, context={
                "track_title": self.track_json.get("title"),
                "codec": codec
            })
            progress_label.update(error_msg)
            self.query_one("#progress_bar").remove()
            await asyncio.sleep(2)
            self.query_one("#progress_bar_container").remove()
            return
        
        await asyncio.sleep(1)

        # Get the m3u8 URL from the transcoding URL
        try:
            progress_label.update("Fetching m3u8 URL...")
            m3u8_url = get_m3u8_url(transcoding['url'], self.track_json, client_id, oauth)
            progress_label.update("m3u8 URL obtained.")
        except Exception as e:
            error_msg = "Failed to retrieve m3u8 URL"
            log_error(e, context={
                "track_title": self.track_json.get("title"),
                "transcoding_url": transcoding.get('url')
            })
            progress_label.update(error_msg)
            self.query_one("#progress_bar").remove()
            await asyncio.sleep(2)
            self.query_one("#progress_bar_container").remove()
            return
        
        await asyncio.sleep(1)
        
        progress_label.update("Starting download of stream via ffmpeg...")
        progress_bar.update(total=transcoding["duration"])

        try:
            async for event in download_stream_ffmpeg(
                url=m3u8_url,
                output_filename=file_name,
                output_path=self.output_path,
                codec=codec,
                track_json=self.track_json,
                oauth=oauth
            ):
                if isinstance(event, ProgressEvent):
                    progress_bar.update(progress=event.progress, total=event.total)
                elif isinstance(event, StageEvent):
                    progress_label.update(event.message)
        except Exception as e:
            safeErr = escape(str(e))
            error_msg = f"[red]Error:[/] {safeErr}"
            log_error(e, context={
                "track_title": self.track_json.get("title"),
                "output_file": f"{self.output_path}/{file_name}"
            })
            progress_label.update(error_msg)
            return

        # due to the difference in the duration of the transcoding and the track, 
        # we need to update the progress bar to the actual duration of the track so it doesn't show up as unfinished
        progress_bar.update(total=self.track_json["duration"], progress=self.track_json["duration"])
        progress_label.update(f"Download completed and saved to {self.output_path}/{file_name}")


app = SoundCloudDownloaderApp()
app.run()
