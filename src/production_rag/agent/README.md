# Agent

This package contains the current read path for the repository: a `RagAgent` wrapper that builds a multi-agent Agno `Team`, mounts it into AgentOS, and answers questions against the Bank of Ghana knowledge base.

## What The Current Code Builds

`rag_agent.py` no longer exposes the older `create_rag_agent()` function described in previous docs. The checked-in implementation centers on the `RagAgent` class.

At initialization time, `RagAgent` currently:

- selects a model with `_get_model(...)`
- creates the shared knowledge base through `create_knowledge_base()`
- optionally connects to Postgres for storage and memory
- creates three specialized agents
- assembles them into a coordinating Agno `Team`

The team members are:

- `Report Directory Agent`
- `Financial Analyst Agent`
- `Chart Agent`

Those prompts live in [prompts.py](prompts.py) and are specific to Bank of Ghana annual reports from 2013 through 2024.

## Files

### [rag_agent.py](rag_agent.py)

Defines `RagAgent`.

Important behavior in the current file:

- default model name is `gpt-5.2`
- model dispatch supports OpenAI, Claude, DeepSeek, and a LiteLLM fallback
- team state and memory use `AsyncPostgresDb` with schema `bog_rag`
- `perform_rag_analysis(...)` delegates to `self.rag_team.print_response(...)`
- MLflow setup is only invoked when `evaluation=True`

### [knowledge.py](knowledge.py)

Builds the shared `Knowledge` object used by the team.

Current implementation details:

- embedder: `snowflake/snowflake-arctic-embed-l`
- reranker: Cohere `rerank-v3.5`
- vector store: Qdrant
- content store: `AsyncPostgresDb`
- `max_results=50`

This module requires `QDRANT_URL`, `QDRANT_API_KEY`, `COLLECTION_NAME`, and `DATABASE_URL` in the environment.

### [prompts.py](prompts.py)

Contains the prompt strings for:

- `REPORT_DIRECTORY_AGENT`
- `FINANCIAL_ANALYST_AGENT`
- `CHART_AGENT`
- `FINANCIAL_AGENT_MANAGER_PROMPT`

These prompts assume a fixed corpus of Bank of Ghana annual reports and hard-code the known filenames for 2013 to 2024.

### [entrypoint.py](entrypoint.py)

This is the checked-in runtime entrypoint for the agent service.

It currently:

- instantiates `RagAgent()`
- registers `rag_agent.rag_team` with `AgentOS`
- exposes `app = agent_os.get_app()`
- serves on port `7777` when run directly

Run it with:

```bash
python -m production_rag.agent.entrypoint
```

## Current Runtime Shape

```text
request
  -> AgentOS
  -> Financial Analyst Team
     -> Report Directory Agent
     -> Financial Analyst Agent
     -> Chart Agent
  -> shared Qdrant knowledge base
  -> shared Postgres-backed state and memory
```

## Configuration

`config/config.yaml` currently contains:

```yaml
llm:
  model_id: "gpt-5.2"
  temperature: 0.2

embedder:
  model_id: "snowflake/snowflake-arctic-embed-l"
  dimensions: 1024

reranker:
  model: "rerank-v3.5"
  top_n: 8
```

The current code reads the embedder and reranker configuration from this file, but `RagAgent` itself hard-codes the default constructor argument `model_name="gpt-5.2"` rather than reading `llm.model_id` directly.

## Notes On Drift Inside The Codebase

Other parts of the repository still refer to an older API:

- `pyproject.toml` declares `rag-cli = "production_rag.cli:main"`, but `production_rag.cli` is not present in this checkout.
- `src/production_rag/rag_evaluation/ragas_eval.py` imports `create_rag_agent()` from this package, but the current file defines `RagAgent` instead.

This README reflects the code as it exists now rather than the older interface those files still expect.
