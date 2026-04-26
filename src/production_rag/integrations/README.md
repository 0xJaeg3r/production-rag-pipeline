# Integrations

This package contains the current MLflow helper code for the repository. It is focused on three responsibilities:

- setting the tracking URI and experiment
- optionally enabling Agno autologging
- creating an OpenAI-compatible client that routes through the MLflow AI Gateway

## File

### [mlflow.py](mlflow.py)

The module currently exports three helpers.

#### `setup_mlflow(autolog: bool = False) -> None`

Current behavior:

- reads `MLFLOW_TRACKING_URI` from the environment
- reads the experiment name from `config/config.yaml`
- calls `mlflow.agno.autolog()` only when `autolog=True`
- catches exceptions and falls back to running without tracing

#### `get_mlflow_prompt(prompt_uri: str, fallback: str) -> str`

Current behavior:

- loads a prompt through `mlflow.genai.load_prompt(...)`
- returns `prompt.format()`
- falls back to the provided string if the registry lookup fails

#### `get_gateway_llm(endpoint: str | None = None) -> OpenAILike`

Current behavior:

- defaults the endpoint from `config/config.yaml`
- points `base_url` at `"{MLFLOW_TRACKING_URI}/gateway/mlflow/v1"`
- returns an `agno.models.openai.OpenAILike` instance

## Configuration

`config/config.yaml` currently contains:

```yaml
mlflow:
  experiment_name: "RAG Agent"
  gateway_endpoint: "open-ai"
```

The helper loader exposes:

- `mlflow_experiment_name`
- `gateway_endpoint`

## Where The Current Code Uses This Package

- `src/production_rag/agent/rag_agent.py` imports `setup_mlflow` and `get_gateway_llm`
- `src/production_rag/rag_evaluation/ragas_eval.py` calls `setup_mlflow(autolog=False)`

## Important Current Behavior

The older docs described MLflow tracing as the default interactive path. That is not what the checked-in code does today.

As currently written:

- `RagAgent` only calls `setup_mlflow(...)` when it is constructed with `evaluation=True`
- the evaluation module calls `setup_mlflow(autolog=False)` and then manages traces explicitly with decorators and MLflow trace APIs

So this package still provides the tracing hooks, but the repository does not currently enable Agno autologging for the normal AgentOS entrypoint by default.
