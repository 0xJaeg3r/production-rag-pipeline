# Evaluation

This package contains the repository's MLflow + RAGAS evaluation script and the static question set it uses.

## Current Files

### [ragas_eval.py](ragas_eval.py)

This is the evaluation entrypoint declared by `pyproject.toml`.

Current responsibilities:

- load questions from `eval_questions.json`
- initialize MLflow with `setup_mlflow(autolog=False)`
- run each question through the agent
- attach reference answers with `mlflow.log_expectation(...)`
- evaluate traces with RAGAS scorers

Current scorer list:

- `Faithfulness`
- `AnswerRelevancy`
- `ContextPrecision`
- `ContextRecall`
- `ContextEntityRecall`

The judge model is configured in `config/config.yaml` as:

```yaml
judge_model: "openai:/gpt-4o-mini"
```

### [eval_questions.json](eval_questions.json)

This file is the default question source. `DEFAULT_QUESTIONS_PATH` points to it directly from `ragas_eval.py`.

Each item is expected to contain:

- `question`
- optional `reference`

Reference answers are used for the reference-based RAGAS scorers.

## Entry Points

The current repository exposes:

```bash
rag-eval
python -m production_rag.rag_evaluation.ragas_eval
```

For a custom file:

```bash
python -c "from production_rag.rag_evaluation.ragas_eval import run_evaluation; run_evaluation('path/to/questions.json')"
```

## Important Current Limitation

`ragas_eval.py` currently imports:

```python
from production_rag.agent.rag_agent import create_rag_agent
```

but the checked-in `src/production_rag/agent/rag_agent.py` defines `RagAgent` and does not expose `create_rag_agent()`.

So the evaluation README can accurately describe the module and its declared entrypoints, but the current snapshot still has an unresolved interface mismatch between the evaluation code and the agent module.

## Implementation Details In The Current File

- `nest_asyncio.apply()` runs at import time
- retrieval spans are built with `@mlflow.trace(span_type=SpanType.RETRIEVER)`
- evaluation forces sequential execution through:

```python
os.environ["MLFLOW_GENAI_EVAL_MAX_WORKERS"] = "1"
os.environ["MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS"] = "1"
```

- LiteLLM callbacks are cleared before `mlflow.genai.evaluate(...)`

## Data Flow

```text
eval_questions.json
  -> run_evaluation(...)
  -> agent response + retriever trace
  -> MLflow trace objects
  -> mlflow.genai.evaluate(...)
  -> results logged to MLflow
```
