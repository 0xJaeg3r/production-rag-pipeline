# Integrations

This module connects the pipeline to MLflow for tracing, prompt management, and LLM routing.

## Why MLflow?

When you run a RAG pipeline, a lot happens between the user's question and the final answer — embedding, retrieval, reranking, LLM calls. If something goes wrong (bad answers, slow responses, hallucinations), you need to see what happened at each step. MLflow records the full trace of every query so you can inspect it later.

It also gives you:
- **AI Gateway** — route LLM calls through MLflow instead of calling OpenAI directly, so you manage API keys in one place
- **Prompt Registry** — version your prompts and update them without changing code
- **Evaluation** — run RAGAS scorers and see results in a dashboard

## Module

### `mlflow.py`
Three functions:

- **`setup_mlflow(autolog)`** — Points MLflow at your server and experiment. If `autolog=True`, every agent query is automatically traced with zero extra code.

- **`get_mlflow_prompt(prompt_uri, fallback)`** — Pulls a prompt from the MLflow Prompt Registry. If the registry is down, it falls back to the hardcoded string so your app keeps working.

- **`get_gateway_llm(endpoint)`** — Returns an LLM that routes through the MLflow AI Gateway instead of calling OpenAI directly. This lets you manage API keys and rate limits centrally in MLflow.

## Configuration

| Env Var | Default | What it does |
|---------|---------|-------------|
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | Where your MLflow server runs |
| `MLFLOW_EXPERIMENT_NAME` | `RAG Agent` | Groups all traces and runs together |

## Switching between direct LLM and Gateway

In `agent/rag_agent.py`, you can toggle between calling OpenAI directly or routing through MLflow:

```python
# Direct — your app talks to OpenAI
llm = OpenAIChat(id="gpt-4o", temperature=0.4, api_key=llm_cfg.api_key)

# Gateway — your app talks to MLflow, MLflow talks to OpenAI
llm = get_gateway_llm("open-ai")
```

Same for prompts:

```python
# Hardcoded in code
active_prompt = SYSTEM_PROMPT

# Pulled from MLflow (can update without redeploying)
active_prompt = get_mlflow_prompt("prompts:/bog_financial_analyst/1", SYSTEM_PROMPT)
```

## What you see in the MLflow UI

After running `rag-cli` and asking a question, open `http://localhost:5000`:

- **Experiments tab** — Groups all runs and traces for the "RAG Agent" experiment
- **Traces tab** — The full chain for each query: user question → knowledge search → LLM call → answer. Shows latency, token usage, and the actual prompts/responses. This is where you debug why the agent gave a certain answer.
- **Runs tab** — Aggregated metrics (tokens, latency) per interaction. Useful for comparing performance across queries.
- **AI Gateway tab** — Configured endpoints and which provider/model they route to
- **Prompt Registry tab** — Versioned prompts that you can update without touching code

## Autolog explained

Autolog is a hook that MLflow registers into Agno. Once enabled, every time the agent runs a query, MLflow automatically records a trace of everything that happened — the question, the knowledge search, the LLM call, and the answer. You don't write any tracing code; it just happens.

**Turn it ON** for normal use (CLI, interactive queries) — you get free tracing of every interaction.

**Turn it OFF** for evaluation — the eval script builds its own traces manually so it has precise control over what goes into each trace. If autolog is also running, you get duplicate or garbled traces that break the RAGAS scorers.

| Situation | Setting | Why |
|---|---|---|
| Interactive / CLI use | `setup_mlflow(autolog=True)` | Free automatic tracing |
| Running evaluation | `setup_mlflow(autolog=False)` | Eval builds traces manually |

### The litellm conflict (if you hit a hang during eval)

`mlflow.genai.evaluate()` quietly re-enables autolog internally, even if you turned it off. This creates a race condition in litellm's async workers that hangs the eval script. The fix is to clear all litellm callbacks before calling `evaluate()` — this is already done in `eval/ragas_eval.py`. If you see a hang at 0%, this is why.
