"""Centralized settings — single source of truth for all configuration."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

@dataclass(frozen=True)
class LLMConfig:
    api_key : str = os.getenv("OPENAI_API_KEY")
    model_id: str = "gpt-4o"
    temperature: float = 0.4

@dataclass(frozen=True)
class QdrantConfig:
    url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key: str = os.getenv("QDRANT_API_KEY", "")
    collection_name: str = os.getenv("COLLECTION_NAME", "")


@dataclass(frozen=True)
class EmbedderConfig:
    model_id: str = "BAAI/bge-base-en-v1.5"
    dimensions: int = 768


@dataclass(frozen=True)
class RerankerConfig:
    model: str = "rerank-v3.5"
    top_n: int = 5


@dataclass(frozen=True)
class MLflowConfig:
    tracking_uri: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    experiment_name: str = os.getenv("MLFLOW_EXPERIMENT_NAME", "RAG Agent")


@dataclass(frozen=True)
class VisionConfig:
    api_url: str = os.getenv("VLLM_API_URL", "")
    model: str = "Qwen/Qwen3-VL-8B-Instruct"


qdrant = QdrantConfig()
embedder = EmbedderConfig()
reranker = RerankerConfig()
mlflow_cfg = MLflowConfig()
vision = VisionConfig()
llm = LLMConfig()