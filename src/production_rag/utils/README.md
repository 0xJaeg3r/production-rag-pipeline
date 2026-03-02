# Utils

Shared helper functions used across the pipeline.

## `image_encoding.py`

Converts local image files into base64 data URIs. This is needed because the vLLM vision model API expects images as base64 strings embedded in the request, not as file paths.

- `image_to_base64(image_path)` — reads an image file, encodes it as base64, and wraps it in a `data:{mime_type};base64,...` URI string
- Automatically detects the MIME type from the file extension (PNG, JPG, JPEG, GIF, WebP)

Used by `ingestion/vision_client.py` when sending page images to the vision model for text extraction.
