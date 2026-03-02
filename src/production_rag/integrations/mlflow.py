"""MLflow setup, prompt registry, and AI Gateway wiring."""

import mlflow
from agno.models.openai import OpenAILike

from production_rag.config import mlflow_cfg


def setup_mlflow(autolog: bool = False) -> None:
    try:
        mlflow.set_tracking_uri(mlflow_cfg.tracking_uri)
        mlflow.set_experiment(mlflow_cfg.experiment_name)
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


def get_gateway_llm(endpoint: str = "open-ai") -> OpenAILike:
    """Return an LLM that routes through the MLflow AI Gateway."""
    return OpenAILike(
        id=endpoint,
        base_url=f"{mlflow_cfg.tracking_uri}/gateway/mlflow/v1",
        api_key="dummy",
        temperature=0.4,
    )
