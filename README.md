# Production RAG Pipeline

This repository is a Bank of Ghana RAG application built around two concrete flows:

1. `src/production_rag/ingestion_pipeline/` extracts PDF pages with a vision model, caches the extracted text as JSON, and indexes the text into Qdrant through Agno `Knowledge`.
2. `src/production_rag/agent/` assembles a multi-agent Agno team backed by Qdrant and Postgres, then exposes it through AgentOS.

This README set describes the code that is currently checked in, including a few entrypoint mismatches that still exist in the repository.

## Current Architecture

```text
PDFs in document-store/
  -> pdf2image page renders in output_images/
  -> VLLM vision extraction to output_store/<pdf>/page_N.json
  -> Agno Knowledge.insert(...)
  -> Qdrant vector store + Postgres contents_db

User request
  -> RagAgent
  -> Agno Team coordinator
  -> Report Directory Agent / Financial Analyst Agent / Chart Agent
  -> model response through AgentOS
```

## Project Layout

```text
production-rag-pipeline/
├── README.md
├── pyproject.toml
├── .env.example
├── docker-compose-prometheus-grafana.yaml
├── grafana.json
├── prometheus.yml.example
├── output_store/                   # extraction cache + manifest.json
├── src/
│   └── production_rag/
│       ├── agent/
│       │   ├── README.md
│       │   ├── entrypoint.py
│       │   ├── knowledge.py
│       │   ├── prompts.py
│       │   ├── rag_agent.py
│       │   └── config/
│       ├── ingestion_pipeline/
│       │   ├── README.md
│       │   ├── chunker.py
│       │   ├── manifest.py
│       │   ├── run_pipeline.py
│       │   ├── document-store/
│       │   ├── pdf_ingestion_pipeline/
│       │   └── config/
│       ├── integrations/
│       │   ├── README.md
│       │   ├── mlflow.py
│       │   └── config/
│       ├── rag_evaluation/
│       │   ├── README.md
│       │   ├── ragas_eval.py
│       │   ├── eval_questions.json
│       │   └── config/
│       └── charts/
└── test_qdrant.py
```

Module docs:

- [ingestion_pipeline](src/production_rag/ingestion_pipeline/README.md)
- [agent](src/production_rag/agent/README.md)
- [integrations](src/production_rag/integrations/README.md)
- [rag_evaluation](src/production_rag/rag_evaluation/README.md)

## Dependencies and Services

The current code expects these external services:

- Qdrant for vector storage
- Postgres for Agno `contents_db`, team state, and memory
- A vLLM-compatible vision endpoint for PDF extraction
- OpenAI for the default chat model and the evaluation judge model
- Cohere for reranking
- MLflow for tracing and evaluation logging

The key Python dependencies declared in `pyproject.toml` include `agno`, `qdrant-client`, `fastembed`, `ragas`, `mlflow[genai]`, `cohere`, `pdf2image`, `psycopg[binary]`, and `anthropic`.

## Environment Variables

`.env.example` covers most of the runtime configuration, but the current code also requires `DATABASE_URL`.

Minimum environment for the checked-in code:

```dotenv
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
COLLECTION_NAME=bank_of_ghana_reports
DATABASE_URL=postgresql+psycopg_async://user:password@localhost:5432/production_rag
VLLM_API_URL=https://your-pod-id-8000.proxy.runpod.net
OPENAI_API_KEY=
COHERE_API_KEY=
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=RAG Agent
```

Notes:

- `DATABASE_URL` is read by both the agent and ingestion code. `chunker.py` derives a sync Postgres URL from it by replacing `+psycopg_async` with `+psycopg`.
- The default agent model in `src/production_rag/agent/config/config.yaml` is `gpt-5.2`.
- If you switch the agent to Claude, you will also need the corresponding Anthropic credentials in your environment.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e .
cp .env.example .env
```

`pdf2image` also requires Poppler:

```bash
# Ubuntu / Debian
sudo apt install poppler-utils

# macOS
brew install poppler
```

For MLflow:

```bash
mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

## Current Entry Points

### Ingestion

The ingestion commands in the repository are current and point to `production_rag.ingestion_pipeline.run_pipeline`:

```bash
rag-ingest
python -m production_rag.ingestion_pipeline.run_pipeline
python -m production_rag.ingestion_pipeline.run_pipeline --step extract
python -m production_rag.ingestion_pipeline.run_pipeline --step index
python -m production_rag.ingestion_pipeline.run_pipeline --clear-indexed
```

Place source PDFs in `src/production_rag/ingestion_pipeline/document-store/`.

### Agent Service

The checked-in agent entrypoint is `src/production_rag/agent/entrypoint.py`, which builds a `RagAgent`, registers its team with AgentOS, and serves the app on port `7777` when run as a module:

```bash
python -m production_rag.agent.entrypoint
```

The packaged `rag-cli` console script in `pyproject.toml` still points to `production_rag.cli:main`, but `src/production_rag/cli.py` is not present in this checkout.

### Evaluation

The declared evaluation entrypoints target `src/production_rag/rag_evaluation/ragas_eval.py`:

```bash
rag-eval
python -m production_rag.rag_evaluation.ragas_eval
```

The evaluation module currently imports `create_rag_agent()` from `production_rag.agent.rag_agent`, while the checked-in agent module exposes a `RagAgent` class instead. The README in `rag_evaluation/` calls that out directly.

## Monitoring

The monitoring files in the repository are still:

- `docker-compose-prometheus-grafana.yaml`
- `prometheus.yml.example`
- `grafana.json`

Start them with:

```bash
docker compose -f docker-compose-prometheus-grafana.yaml up -d
```

Default URLs:

- Grafana: `http://localhost:3000`
- Prometheus: `http://localhost:9090`
- MLflow: `http://localhost:5000`

## What Changed From The Older Docs

The old README set described a simpler single-agent CLI flow and older retrieval settings. The checked-in code now uses:

- `RagAgent` and an Agno `Team`, not a documented `create_rag_agent()` factory
- `snowflake/snowflake-arctic-embed-l` embeddings, not the previously documented BGE model
- fixed-size chunking during ingestion, not semantic chunking
- Postgres-backed Agno content tracking during ingestion
- parallel extraction but single-threaded indexing for reliability on the sync Agno/Postgres path
- repo-root `output_store/manifest.json` as the extraction and indexing state file

## License

MIT
