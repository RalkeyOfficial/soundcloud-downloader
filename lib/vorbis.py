import base64
import struct
import requests

def make_picture_block(url: str) -> str:
    # 1) fetch your artwork.jpg (in memory)
    resp = requests.get(url)
    resp.raise_for_status()
    img_data = resp.content

    # 2) VorbisPicture header fields
    pic_type    = 3  # 3 = “cover (front)”
    mime        = b"image/jpeg"
    desc        = b"Cover (front)"
    width = height = 0
    depth = 0
    colors = 0

    # 3) build the binary block
    parts = []
    pack = struct.pack
    parts.append(pack(">I", pic_type))
    parts.append(pack(">I", len(mime)) + mime)
    parts.append(pack(">I", len(desc)) + desc)
    parts.append(pack(">I", width) + pack(">I", height))
    parts.append(pack(">I", depth) + pack(">I", colors))
    parts.append(pack(">I", len(img_data)) + img_data)

    block = b"".join(parts)
    return base64.b64encode(block).decode("ascii")