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

# if this file is imported, exit
if __name__ != "__main__":
    exit()


import argparse
import subprocess
import sys
import re
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


VERSION = "2.0.1"
AUTHOR = "Ralkey"


try:
    subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
except (subprocess.SubprocessError, FileNotFoundError):
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


# get user info
try:
    user_info = get_account_info(client_id, oauth)
except Exception as e:
    user_info["username"] = "Unknown"


class SoundCloudDownloaderApp(App):
    CSS_PATH = "styles/style.tcss"

    def __init__(self):
        super().__init__()
        self.track_valid = False
        self.track_json = {}

    def on_mount(self) -> None:
        self.screen.styles.border = ("solid", Color(255, 85, 0))

    def compose(self) -> ComposeResult:
        with Container(id="header_container"):
            yield Label("SoundCloud HLS Downloader", id="title")
            yield Label(f"v{VERSION} - By Ralkey", id="subtitle")

        yield Label(f"Logged in as {user_info['username']}", id="user_info", classes=("full_width"))

        with Container(id="input_container"):
            yield Input(type="text", placeholder="SoundCloud URL", id="url_input", validators=[
                Regex(regex=r"^https:\/\/soundcloud\.com\/[^/]+/[^/]+$")
            ])
            with Container(id="options_container"):
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
            yield Button("Download", id="download_button", disabled=True, classes=("button_class"))


    def update_download_button(self) -> None:
        download_button = self.query_one("#download_button")
        download_button.disabled = not self.track_valid

    @on(Input.Changed, "#url_input")
    async def update_file_name(self, event: Input.Changed) -> None:
        file_name_input = self.query_one("#file_name_input")

        # reset values to prepare for new fetch
        self.track_json = {}
        file_name_input.clear()
        # mark track as invalid until new data is fetched
        self.track_valid = False
        self.update_download_button()
        
        await self.fetch_track_info(event=event)

    @debounce_async(delay_seconds=0.5)
    async def fetch_track_info(self, event):
        file_name_input = self.query_one("#file_name_input")

        try:
            self.track_json = resolve_track(event.value, client_id, oauth)

            file_name_input.clear()
            file_name_input.insert(self.track_json["title"], 0)
            # Mark track as valid
            self.track_valid = True
        except Exception as e:
            self.track_valid = False

        # update button state
        self.update_download_button()


    @on(Button.Pressed, "#download_button")
    async def start_download(self, event: Button.Pressed) -> None:
        input_container = self.query_one("#input_container")

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
        output_path = "./output"

        # Get the highest quality HLS transcoding URL
        try:
            progress_label.update("Getting HLS transcoding URL...")
            transcoding = get_hls_transcoding(self.track_json, codec)
            progress_label.update("HLS transcoding URL resolved.")
        except Exception as e:
            progress_label.update("No HLS transcoding found for this track.")
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
            progress_label.update("Failed to retrieve m3u8 URL.")
            self.query_one("#progress_bar").remove()
            await asyncio.sleep(2)
            self.query_one("#progress_bar_container").remove()
            return
        
        await asyncio.sleep(1)
        
        progress_label.update("Starting download of stream via ffmpeg...")
        progress_bar.update(total=transcoding["duration"])

        try:
            async for ms in download_stream_ffmpeg(
                url=m3u8_url,
                output_filename=file_name,
                output_path=output_path,
                codec=codec,
                track_json=self.track_json,
                oauth=oauth
            ):
                progress_bar.update(progress=ms // 1000)
        except Exception as e:
            # Export error to log file
            # with open("soundcloud_error.log", "w") as f:
            #     f.write(f"Error occurred during download:\n{str(e)}")
            safeErr = escape(str(e))
            progress_label.update(f"[red]Error:[/] {safeErr}")
            return

        progress_label.update(f"Download completed and saved to {output_path}/{file_name}")

        pass


app = SoundCloudDownloaderApp()
app.run()
