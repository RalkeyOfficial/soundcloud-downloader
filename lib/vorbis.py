import base64
import struct
import requests

def make_picture_block_from_url(url: str) -> str:
    # 1) fetch your artwork.jpg (in memory)
    resp = requests.get(url)
    resp.raise_for_status()
    return make_picture_block_from_bytes(resp.content)

def make_picture_block_from_path(path: str) -> str:
    # 1) fetch your artwork.jpg (in memory)
    with open(path, "rb") as f:
        img_data = f.read()

    return make_picture_block_from_bytes(img_data)

def make_picture_block_from_bytes(img_bytes: bytes) -> str:
    pic_type    = 3
    mime        = b"image/jpeg"
    desc        = b"Cover (front)"
    width = height = 0
    depth = 0
    colors = 0

    parts = []
    pack = struct.pack
    parts.append(pack(">I", pic_type))
    parts.append(pack(">I", len(mime)) + mime)
    parts.append(pack(">I", len(desc)) + desc)
    parts.append(pack(">I", width) + pack(">I", height))
    parts.append(pack(">I", depth) + pack(">I", colors))
    parts.append(pack(">I", len(img_bytes)) + img_bytes)

    block = b"".join(parts)
    return base64.b64encode(block).decode("ascii")
