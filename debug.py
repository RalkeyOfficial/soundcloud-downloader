#!/usr/bin/env python3
"""
SoundCloud Downloader Debug Script

This script helps debug the SoundCloud downloader by testing each component
with a specified URL and providing detailed output about what's happening.
"""

import argparse
import sys
import json
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from lib.soundcloud import (
    resolve_track,
    get_hls_transcoding,
    get_m3u8_url,
    download_stream_ffmpeg,
    get_account_info
)
from lib.config import load_config

console = Console()

def debug_track_resolution(url: str, client_id: str, oauth: str = None) -> dict:
    """Debug the track resolution process."""
    console.print("\n[bold cyan]1. Resolving Track Information[/]")
    try:
        track_info = resolve_track(url, client_id, oauth)
        console.print(Panel(
            json.dumps(track_info, indent=2),
            title="Track Information",
            border_style="green"
        ))
        return track_info
    except Exception as e:
        console.print(f"[red]Error resolving track:[/] {str(e)}")
        sys.exit(1)

def debug_hls_transcoding(track_info: dict, codec: str = "mp3") -> dict:
    """Debug the HLS transcoding process."""
    console.print("\n[bold cyan]2. Getting HLS Transcoding[/]")
    try:
        transcoding = get_hls_transcoding(track_info, codec)
        console.print(Panel(
            json.dumps(transcoding, indent=2),
            title="HLS Transcoding Information",
            border_style="green"
        ))
        return transcoding
    except Exception as e:
        console.print(f"[red]Error getting HLS transcoding:[/] {str(e)}")
        sys.exit(1)

def debug_m3u8_url(transcoding: dict, track_info: dict, client_id: str, oauth: str = None) -> str:
    """Debug the m3u8 URL resolution process."""
    console.print("\n[bold cyan]3. Getting m3u8 URL[/]")
    try:
        m3u8_url = get_m3u8_url(transcoding, track_info, client_id, oauth)
        console.print(Panel(
            m3u8_url,
            title="m3u8 URL",
            border_style="green"
        ))
        return m3u8_url
    except Exception as e:
        console.print(f"[red]Error getting m3u8 URL:[/] {str(e)}")
        sys.exit(1)

def debug_download(m3u8_url: str, output_filename: str, track_info: dict, oauth: str = None):
    """Debug the download process."""
    console.print("\n[bold cyan]4. Testing Download Process[/]")
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Downloading...", total=None)
            
            # Test the download process
            async def test_download():
                async for ms in download_stream_ffmpeg(
                    url=m3u8_url,
                    output_filename=output_filename,
                    output_path="./output",
                    codec="mp3",
                    track_json=track_info,
                    oauth=oauth
                ):
                    progress.update(task, description=f"Downloading... ({ms}ms)")
            
            import asyncio
            asyncio.run(test_download())
            
        console.print("[green]Download test completed successfully![/]")
    except Exception as e:
        console.print(f"[red]Error during download:[/] {str(e)}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Debug the SoundCloud downloader")
    parser.add_argument("--url", help="SoundCloud track URL")
    parser.add_argument("--config", default="config.json", help="Path to configuration file")
    parser.add_argument("--client-id", help="SoundCloud client ID")
    parser.add_argument("--oauth", help="SoundCloud OAuth token")
    parser.add_argument("--output", default="debug_output", help="Output filename")

    args = parser.parse_args()
    
    args.url = "https://soundcloud.com/vincent-gillberg-holm/maxwell-the-cat-theme1-hour-version"

    # Load configuration
    config = {}
    if not all([args.client_id, args.oauth]):
        try:
            config = load_config(args.config)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config file:[/] {str(e)}")
    
    # Use command-line args or config values
    client_id = args.client_id or config.get("client_id")
    oauth = args.oauth or config.get("oauth")
    
    if not client_id:
        console.print("[red]Error: client_id must be provided as argument or in config file[/]")
        sys.exit(1)
    
    console.print(Panel(
        f"URL: {args.url}\nClient ID: {client_id}\nOAuth: {'Provided' if oauth else 'Not provided'}",
        title="Debug Configuration",
        border_style="blue"
    ))
    
    # Test account info
    try:
        account_info = get_account_info(client_id, oauth)
        console.print(Panel(
            json.dumps(account_info, indent=2),
            title="Account Information",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[yellow]Warning: Could not get account info:[/] {str(e)}")
    
    # Run through all debug steps
    track_info = debug_track_resolution(args.url, client_id, oauth)
    transcoding = debug_hls_transcoding(track_info, codec="mp3")
    m3u8_url = debug_m3u8_url(transcoding["url"], track_info, client_id, oauth)
    debug_download(m3u8_url, args.output, track_info, oauth)
    
    console.print("\n[bold green]All debug steps completed successfully![/]")

if __name__ == "__main__":
    main()
