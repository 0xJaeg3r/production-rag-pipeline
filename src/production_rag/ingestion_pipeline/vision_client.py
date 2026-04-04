"""Client for calling vLLM Vision API endpoint."""

import requests

from production_rag.config import vision as vision_cfg
from production_rag.utils.image_encoding import image_to_base64


class VLLMVisionClient:
    """Sends images to a vLLM-hosted vision model to extract text content."""

    def __init__(self, base_url=None):
        base_url = base_url or vision_cfg.api_url
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/v1/chat/completions"

    def chat_with_image_url(self, text_prompt, image_url, model=None):
        model = model or vision_cfg.model
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_prompt},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            ],
        }

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error calling API: {e}")
            return None

    def chat_with_local_image(self, text_prompt, image_path, model=None):
        model = model or vision_cfg.model
        image_data_uri = image_to_base64(image_path)

        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": text_prompt},
                        {"type": "image_url", "image_url": {"url": image_data_uri}},
                    ],
                }
            ],
        }

        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error calling API: {e}")
            return None

    def extract_response_text(self, response):
        if response and "choices" in response:
            return response["choices"][0]["message"]["content"]
        return None
