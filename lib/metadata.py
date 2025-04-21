import requests
import imghdr
from mutagen.oggvorbis import OggVorbis
from mutagen.oggopus import OggOpus
from mutagen.mp3 import MP3
from mutagen.id3 import APIC, ID3, error
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from lib.vorbis import make_picture_block_from_bytes

def _add_ogg_cover(audio, img_bytes):
    """Add cover art to Ogg Vorbis/Opus files"""
    block_b64 = make_picture_block_from_bytes(img_bytes)
    audio["metadata_block_picture"] = [block_b64]

def _add_mp3_cover(audio, img_bytes, mime_type):
    """Add cover art to MP3 files"""
    try:
        audio.add_tags()
    except error:
        pass # Tags already exist

    audio.tags.add(
        APIC(
            encoding=3,
            mime=mime_type,
            type=3,
            desc='Cover',
            data=img_bytes
        )
    )

def _add_flac_cover(audio, img_bytes, mime_type):
    """Add cover art to FLAC files"""
    picture = Picture()
    picture.data = img_bytes
    picture.type = 3
    picture.mime = mime_type
    picture.desc = "Cover"
    picture.width = picture.height = picture.depth = picture.colors = 0

    audio.clear_pictures()
    audio.add_picture(picture)

def _add_aac_cover(audio, img_bytes, mime_type):
    """Add cover art to AAC/M4A files"""
    cover_format = (MP4Cover.FORMAT_JPEG if mime_type == "image/jpeg" 
                   else MP4Cover.FORMAT_PNG if mime_type == "image/png" 
                   else None)
    cover = MP4Cover(img_bytes, imageformat=cover_format)
    audio["covr"] = [cover]

async def add_cover_art_from_url(file_path: str, image_url: str, codec: str):
    """
    Add cover art to an audio file.
    
    Args:
        file_path: Path to the audio file
        image_url: URL of the cover image
        codec: Audio codec ('opus', 'vorbis', 'mp3', 'flac', or 'aac')
    """
    # Read the raw image bytes
    resp = requests.get(image_url)
    resp.raise_for_status()
    img_bytes = resp.content

    # Determine the mime type
    mime_type = resp.headers.get("Content-Type")
    if not mime_type or not mime_type.startswith("image/"):
        kind = imghdr.what(None, img_bytes)
        if kind:
            mime_type = f"image/{kind}"
        else:
            raise ValueError("Could not determine image MIME type")

    # Map codecs to their handlers
    codec_handlers = {
        'opus': (OggOpus, lambda a: _add_ogg_cover(a, img_bytes)),
        'vorbis': (OggVorbis, lambda a: _add_ogg_cover(a, img_bytes)),
        'mp3': (lambda p: MP3(p, ID3=ID3), lambda a: _add_mp3_cover(a, img_bytes, mime_type)),
        'flac': (FLAC, lambda a: _add_flac_cover(a, img_bytes, mime_type)),
        'aac': (MP4, lambda a: _add_aac_cover(a, img_bytes, mime_type))
    }

    if codec not in codec_handlers:
        raise ValueError(f"Unsupported codec: {codec}")

    # load audio class and handler from a specific codec
    AudioClass, handler = codec_handlers[codec]
    # Load the audio file in its prospective codec
    audio = AudioClass(file_path)
    # Apply the handler to the audio file
    handler(audio)
    # Save the audio file
    if isinstance(audio, MP3):
        audio.save(v2_version=4) # save as v2.4 - only v2.4 supports png cover art
    else:
        audio.save()