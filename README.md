# Production RAG Pipeline

A complete, production-grade RAG (Retrieval-Augmented Generation) pipeline that you can learn from and adapt. It takes PDF documents, extracts their content using a vision model, stores it in a vector database, and lets you ask questions about it using an LLM — with full tracing, evaluation, and monitoring.

Built around the Bank of Ghana Annual Report, but the approach works for any PDF-heavy domain.

## What is RAG?

RAG stands for Retrieval-Augmented Generation. Instead of asking an LLM to answer from memory (which leads to hallucination), you first **retrieve** relevant documents from a database, then **generate** an answer grounded in those documents. The LLM only sees what you give it, so it stays factual.

## How This Pipeline Works

```
PDF → Images → Vision LLM (text extraction) → Chunking & Embedding → Qdrant Vector Store
                                                                              |
                                              User Query → Retrieval + Reranking → LLM → Answer
                                                                              |
                                                                    MLflow (traces, eval)
```

There are three main stages:

1. **Ingestion** (getting data into the system)
   - Each PDF page is converted to an image
   - A vision model reads the image and extracts the text (this handles tables, charts, and layouts that regular PDF parsers miss)
   - The text is split into smaller chunks and stored as vectors in Qdrant

2. **Querying** (asking questions)
   - Your question gets embedded into the same vector space
   - The most relevant chunks are retrieved from Qdrant
   - A reranker scores the chunks and picks the best ones
   - The LLM reads those chunks and writes a grounded answer

3. **Evaluation** (measuring quality)
   - A set of questions with known correct answers is run through the pipeline
   - RAGAS scorers measure whether the answers are faithful, relevant, and well-supported by the retrieved context
   - Everything is logged to MLflow so you can track quality over time

## Project Structure

```
production-rag/
├── pyproject.toml
├── .env / .env.example
├── data/
│   └── eval_questions.json           # Questions with correct answers for evaluation
├── src/
│   ├── pdf-store/                    # Drop your PDFs here
│   └── production_rag/              # Main Python package
│       ├── config.py                 # All settings in one place
│       ├── cli.py                    # Chat interface
│       ├── ingestion/                # PDF → text → vectors
│       ├── agent/                    # The RAG agent that answers questions
│       ├── integrations/             # MLflow tracing and LLM routing
│       ├── eval/                     # Quality measurement with RAGAS
│       └── utils/                    # Helper functions
├── docker-compose-prometheus-grafana.yaml
├── prometheus.yml.example
└── grafana.json
```

Each module has its own README that explains what it does and why:
- [ingestion/](src/production_rag/ingestion/README.md) — How PDFs become searchable vectors
- [agent/](src/production_rag/agent/README.md) — How the RAG agent retrieves and answers
- [integrations/](src/production_rag/integrations/README.md) — How MLflow tracks everything
- [eval/](src/production_rag/eval/README.md) — How to measure if your RAG is working well
- [utils/](src/production_rag/utils/README.md) — Shared helper functions

## Tech Stack

| What | Tool | Why |
|------|------|-----|
| PDF to Image | `pdf2image` (poppler) | Preserves tables/charts that text extractors miss |
| Text Extraction | Qwen3-VL-8B via vLLM on RunPod | Vision model reads images like a human would |
| Chunking | `chonkie` (semantic) | Keeps related sentences together, not just fixed-size splits |
| Embeddings | `BAAI/bge-base-en-v1.5` via FastEmbed | Converts text to vectors for similarity search |
| Reranker | Cohere `rerank-v3.5` | Re-scores retrieved chunks so the best ones come first |
| Vector Store | Qdrant Cloud | Stores and searches vectors at scale |
| Query LLM | OpenAI (direct or via MLflow Gateway) | Generates the final answer from retrieved context |
| Agent Framework | Agno | Wires the LLM, knowledge base, and tools together |
| Tracing & Eval | MLflow + RAGAS | Tracks every query and measures answer quality |
| Monitoring | Prometheus + Grafana | System metrics for Qdrant, vLLM, and infrastructure |

## Prerequisites

- Python >= 3.11
- A RunPod instance running vLLM with `Qwen/Qwen3-VL-8B-Instruct` (only needed for ingestion) — see [RunPod setup](src/production_rag/ingestion/README.md#runpod-setup-vision-model)
- A Qdrant Cloud cluster (or local Qdrant instance)
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

Place PDF files in `src/pdf-store/`, then run:

```bash
rag-ingest
# or: python -m production_rag.ingestion.run_pipeline
```

This converts each PDF page to an image, sends it to the vision model for text extraction, chunks the text, and stores the vectors in Qdrant. Pages that are already ingested are skipped, so you can safely rerun if the process gets interrupted.

### Querying — Asking questions

```bash
rag-cli
# or: python -m production_rag.cli
```

This starts an interactive chat. Type a question, and the agent retrieves relevant chunks from Qdrant, reranks them, and generates a grounded answer. Every query is automatically traced in MLflow.

### Evaluation — Measuring answer quality

```bash
rag-eval
# or: python -m production_rag.eval.ragas_eval
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
- The Qdrant collection is created automatically on first ingestion
- Image conversion and page ingestion are both idempotent — safe to rerun
- To re-ingest from scratch, delete `output_images/` and `output_images/.ingested.log`

## License

MIT
