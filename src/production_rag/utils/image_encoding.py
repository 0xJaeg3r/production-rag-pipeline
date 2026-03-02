"""Convert local images to base64 data URIs."""

import base64
from pathlib import Path


def image_to_base64(image_path) -> str:
    """Convert local image to base64 data URI."""
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode("utf-8")

    extension = Path(image_path).suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    mime_type = mime_types.get(extension, "image/jpeg")

    return f"data:{mime_type};base64,{encoded}"
