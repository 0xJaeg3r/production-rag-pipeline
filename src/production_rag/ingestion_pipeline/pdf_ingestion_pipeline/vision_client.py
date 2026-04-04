"""Client for calling vLLM Vision API endpoint."""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv, find_dotenv

from production_rag.ingestion_pipeline.config.config_loader import vision_model

load_dotenv(find_dotenv())

vllm_api_url = os.environ["VLLM_API_URL"]
from production_rag.ingestion_pipeline.pdf_ingestion_pipeline.image_to_base_64 import image_to_base64


class VLLMVisionClient:
    """Sends images to a vLLM-hosted vision model to extract text content."""

    def __init__(self, base_url=None):
        base_url = base_url or vllm_api_url
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/v1/chat/completions"

    def chat_with_image_url(self, text_prompt, image_url, model=None):
        model = model or vision_model
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
        model = model or vision_model
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

    def save_extraction(self, text, output_path, source_file, page_number):
        """Save extracted text to a JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump({
                "source_file": source_file,
                "page_number": page_number,
                "text": text,
            }, f, indent=2)
