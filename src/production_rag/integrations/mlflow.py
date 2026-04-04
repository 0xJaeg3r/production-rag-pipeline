"""MLflow setup, prompt registry, and AI Gateway wiring."""

import os

import mlflow
from agno.models.openai import OpenAILike
from dotenv import load_dotenv, find_dotenv

from production_rag.integrations.config.config_loader import (
    mlflow_experiment_name, gateway_endpoint,
)

load_dotenv(find_dotenv())

mlflow_tracking_uri = os.environ["MLFLOW_TRACKING_URI"]


def setup_mlflow(autolog: bool = False) -> None:
    try:
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        mlflow.set_experiment(mlflow_experiment_name)
        if autolog:
            mlflow.agno.autolog()
    except Exception as e:
        print(f"MLflow not available, running without tracing: {e}")


def get_mlflow_prompt(prompt_uri: str, fallback: str) -> str:
    """Load a prompt from the MLflow Prompt Registry.
    Falls back to the provided string if unavailable."""
    try:
        prompt = mlflow.genai.load_prompt(prompt_uri)
        return prompt.format()
    except Exception as e:
        print(f"Could not load MLflow prompt, using fallback: {e}")
        return fallback


def get_gateway_llm(endpoint: str = None) -> OpenAILike:
    """Return an LLM that routes through the MLflow AI Gateway."""
    endpoint = endpoint or gateway_endpoint
    return OpenAILike(
        id=endpoint,
        base_url=f"{mlflow_tracking_uri}/gateway/mlflow/v1",
        api_key="dummy",
        temperature=0.4,
    )
