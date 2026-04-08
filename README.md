# Production RAG Pipeline

A complete, production-grade RAG (Retrieval-Augmented Generation) pipeline that you can learn from and adapt. It takes PDF documents, extracts their content using a vision model, stores it in a vector database, and lets you ask questions about it using an LLM — with full tracing, evaluation, and monitoring.

Built around the Bank of Ghana Annual Reports (2013–2024), but the approach works for any PDF-heavy domain.

## What is RAG?

RAG stands for Retrieval-Augmented Generation. Instead of asking an LLM to answer from memory (which leads to hallucination), you first **retrieve** relevant documents from a database, then **generate** an answer grounded in those documents. The LLM only sees what you give it, so it stays factual.

## How This Pipeline Works

```
PDF → Images → Vision LLM (text extraction) → Chunking & Embedding → Qdrant Vector Store
                                                                              |
                                              User Query → Retrieval + Reranking → LLM → Answer
                                                                              |
                                                            Multi-Agent Team (Analyst + Chart)
                                                                              |
                                                                    MLflow (traces, eval)
```

There are three main stages:

1. **Ingestion** (getting data into the system — two decoupled steps)
   - **Extract**: Each PDF page is converted to an image, a vision model reads it and extracts text, and the result is cached as a JSON file
   - **Index**: Cached text is split into semantic chunks and stored as vectors in Qdrant
   - If Qdrant is wiped, re-indexing reads from the cache — no expensive vision LLM calls needed

2. **Querying** (asking questions)
   - Your question gets embedded into the same vector space
   - The most relevant chunks are retrieved from Qdrant
   - A reranker scores the chunks and picks the best ones
   - A coordinated team of agents processes the query:
     - **Financial Analyst Agent** — retrieves data, extracts figures, provides citations
     - **Chart Agent** — creates visualizations when the query calls for it
     - **Team Coordinator** — routes queries to the right agent and combines responses
   - Conversation history and user memories persist across sessions via PostgreSQL

3. **Evaluation** (measuring quality)
   - A set of questions with known correct answers is run through the pipeline
   - RAGAS scorers measure whether the answers are faithful, relevant, and well-supported by the retrieved context
   - Everything is logged to MLflow so you can track quality over time

## Project Structure

```
production-rag/
├── pyproject.toml
├── .env / .env.example
├── src/
│   └── production_rag/
│       ├── cli.py                        # Interactive chat interface
│       ├── ingestion_pipeline/           # PDF → text → vectors
│       │   ├── config/                   # YAML config + loader
│       │   ├── pdf_ingestion_pipeline/   # PDF converter + vision client
│       │   ├── docx_ingestion_pipeline/  # (future) DOCX extraction
│       │   ├── document-store/           # Drop your PDFs here
│       │   ├── manifest.py               # Tracks extraction/indexing state
│       │   ├── chunker.py                # Semantic chunking + Qdrant storage
│       │   └── run_pipeline.py           # Pipeline orchestrator
│       ├── agent/                        # Multi-agent RAG team
│       │   ├── rag_agent.py              # Single-agent factory (simple mode)
│       │   ├── rag_agent_with_class.py   # Multi-agent team (full mode)
│       │   ├── entrypoint.py             # FastAPI/AgentOS web service
│       │   ├── knowledge.py              # Knowledge base (Qdrant + reranker)
│       │   ├── prompts.py                # Original prompt instructions
│       │   ├── promptsV2.py              # Specialized agent prompts
│       │   └── config/                   # YAML config + loader
│       ├── integrations/                 # MLflow tracing and LLM routing
│       │   └── config/                   # YAML config + loader
│       ├── rag_evaluation/               # Quality measurement with RAGAS
│       │   └── config/                   # YAML config + loader
│       ├── charts/                       # Generated visualization outputs
│       └── utils/                        # Helper functions
├── docker-compose-prometheus-grafana.yaml
├── prometheus.yml.example
└── grafana.json
```

Each module has its own README and config:
- [ingestion_pipeline/](src/production_rag/ingestion_pipeline/README.md) — How PDFs become searchable vectors
- [agent/](src/production_rag/agent/README.md) — How the RAG agent retrieves and answers
- [integrations/](src/production_rag/integrations/README.md) — How MLflow tracks everything
- [utils/](src/production_rag/utils/README.md) — Shared helper functions

## Tech Stack

| What | Tool | Why |
|------|------|-----|
| PDF to Image | `pdf2image` (poppler) | Preserves tables/charts that text extractors miss |
| Text Extraction | Qwen3-VL-8B via vLLM on RunPod | Vision model reads images like a human would |
| Chunking | `chonkie` (semantic) | Keeps related sentences together, not just fixed-size splits |
| Embeddings | `snowflake/snowflake-arctic-embed-l` via FastEmbed | 1024-dim vectors for similarity search |
| Reranker | Cohere `rerank-v3.5` | Re-scores retrieved chunks so the best ones come first |
| Vector Store | Qdrant Cloud | Stores and searches vectors at scale |
| Query LLM | GPT-5.2 (default), also supports Claude, DeepSeek | Generates the final answer from retrieved context |
| Agent Framework | Agno (Teams + Agents) | Multi-agent coordination, knowledge tools, visualization |
| Storage | PostgreSQL (Neon) | Conversation history, user memories, knowledge metadata |
| Web Service | FastAPI via AgentOS | REST API for serving the agent team |
| Tracing & Eval | MLflow + RAGAS | Tracks every query and measures answer quality |
| Monitoring | Prometheus + Grafana | System metrics for Qdrant, vLLM, and infrastructure |

## Prerequisites

- Python >= 3.11
- A RunPod instance running vLLM with `Qwen/Qwen3-VL-8B-Instruct` (only needed for extraction) — see [RunPod setup](src/production_rag/ingestion_pipeline/README.md#runpod-setup-vision-model)
- A Qdrant Cloud cluster (or local Qdrant instance)
- A PostgreSQL database (e.g. Neon) for conversation history and user memories
- An OpenAI API key
- A Cohere API key (for reranking)
- MLflow server — see [MLflow setup](src/production_rag/integrations/README.md)
- `poppler-utils` installed on your system (required by `pdf2image`)

### Installing poppler

```bash
# Ubuntu/Debian
sudo apt install poppler-utils

# macOS
brew install poppler
```

## Setup

1. **Clone and create a virtual environment**

```bash
git clone <repo-url>
cd production-rag
python -m venv .venv
source .venv/bin/activate
```

2. **Install CPU-only PyTorch first** (saves ~2GB vs the default CUDA version)

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

3. **Install the project**

```bash
pip install -e .
```

4. **Configure environment variables**

```bash
cp .env.example .env
```

Edit `.env` with your actual keys:

```
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key
COLLECTION_NAME=your_collection_name
VLLM_API_URL=https://your-pod-id-8000.proxy.runpod.net
OPENAI_API_KEY=your-openai-api-key
COHERE_API_KEY=your-cohere-api-key
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_EXPERIMENT_NAME=RAG Agent
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
RAG_DATA_DIR=/path/to/local/cache
```

5. **Start MLflow** (for tracing and evaluation)

```bash
mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

Port 5000 avoids conflict with Grafana on 3000. If the port gets stuck:

```bash
lsof -ti :5000 | xargs kill -9
mlflow server --backend-store-uri sqlite:///mlflow.db --host 127.0.0.1 --port 5000
```

## Usage

### Ingestion — Getting your PDFs into the system

Place PDF files in `src/production_rag/ingestion_pipeline/document-store/`, then run:

```bash
# Full pipeline (extract + index)
python -m production_rag.ingestion_pipeline.run_pipeline

# Extract only (no Qdrant needed)
python -m production_rag.ingestion_pipeline.run_pipeline --step extract

# Index only (from cached JSONs, no vision LLM needed)
python -m production_rag.ingestion_pipeline.run_pipeline --step index

# Re-index after Qdrant wipe
python -m production_rag.ingestion_pipeline.run_pipeline --clear-indexed
python -m production_rag.ingestion_pipeline.run_pipeline --step index
```

Extraction sends each page to the vision model and caches the result as JSON in `output_store/`. Indexing reads from the cache, chunks the text, and stores vectors in Qdrant. Already-extracted and already-indexed pages are skipped automatically. Failed pages are retried on the next run.

### Querying — Asking questions

```bash
rag-cli
# or: python -m production_rag.cli
```

This starts an interactive chat. Type a question, and the agent retrieves relevant chunks from Qdrant, reranks them, and generates a grounded answer. Every query is automatically traced in MLflow.

### Evaluation — Measuring answer quality

```bash
rag-eval
# or: python -m production_rag.rag_evaluation.ragas_eval
```

Runs 10 questions with known correct answers through the pipeline. RAGAS scores how faithful, relevant, and well-supported each answer is. Results appear in the MLflow UI under the Evaluations tab.

## Monitoring

### Configure Prometheus

```bash
cp prometheus.yml.example prometheus.yml
```

Edit `prometheus.yml` with your Qdrant credentials and RunPod URL.

### Start the stack

```bash
docker compose -f docker-compose-prometheus-grafana.yaml up -d
```

- Grafana: `http://localhost:3000` (admin/admin)
- Prometheus: `http://localhost:9090`
- MLflow: `http://localhost:5000`

### Configure Prometheus as a Grafana data source

1. Open Grafana at `http://localhost:3000` and log in (default: admin/admin)
2. Go to Configuration (gear icon) → Data Sources → "Add data source"
3. Select Prometheus
4. Set the URL to `http://prometheus:9090` (they share a Docker network)
5. Click "Save & Test"

This gives you dashboards for system resources (Node Exporter), database performance (Qdrant), and inference metrics (vLLM).

### Updating the RunPod URL

When you spin up a new RunPod instance, the proxy URL changes:

1. Update `VLLM_API_URL` in `.env`
2. Update the vLLM target in `prometheus.yml`:
   ```yaml
   - job_name: vllm
     scheme: https
     metrics_path: /metrics
     static_configs:
       - targets:
         - your-new-pod-id-8000.proxy.runpod.net
   ```
3. Restart the stack:
   ```bash
   docker compose -f docker-compose-prometheus-grafana.yaml down
   docker compose -f docker-compose-prometheus-grafana.yaml up -d
   ```

## Notes

- The vision model runs on RunPod (GPU); everything else runs locally on CPU
- The Qdrant collection is created automatically on first indexing
- Extraction and indexing are both idempotent — safe to rerun
- Progress is tracked in `output_store/manifest.json`
- Extracted text is cached in `output_store/` as JSON — re-indexing after a Qdrant wipe is fast
- Each module has its own `config/config.yaml` for static settings; secrets live in `.env`

## License

MIT
