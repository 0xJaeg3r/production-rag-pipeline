# Ingestion Pipeline

This is the "write" side of the RAG pipeline. It takes PDF documents and turns them into searchable vectors stored in Qdrant.

## Why not just parse the PDF text directly?

Most financial reports have complex tables, charts, footnotes, and multi-column layouts. Standard PDF text extractors (like PyPDF2 or pdfplumber) lose the structure and mix up columns. Instead, we convert each page to an image and send it to a vision model that can "read" the page like a human would — tables, formatting, and all.

## How it works

```
PDF file → pdf_to_image_converter.py → page images (PNG)
                                           |
                                 vision_client.py → extracted text → page JSONs (cached)
                                           |
                                    chunker.py → semantic chunks → Qdrant
```

The pipeline runs in two decoupled steps:

1. **Extract** (PDF → images → vision LLM → cached page JSONs)
   - Each PDF page becomes a high-resolution PNG, stored in `output_images/{pdf_name}/`
   - Each image is sent to a Qwen3-VL-8B vision model running on RunPod
   - Extracted text is cached as JSON in `output_store/{pdf_name}/page_N.json`
   - Skips pages that already have a cached JSON

2. **Index** (cached page JSONs → chunks → Qdrant)
   - Reads cached page JSONs from `output_store/`
   - Splits text into semantic chunks and indexes into Qdrant
   - Skips pages already marked as indexed in the manifest

Progress is tracked in `output_store/manifest.json` — no more `.ingested.log` / `.failed.log`.

## Modules

### `pdf_to_image_converter.py`
Converts PDF pages to PNG images using `pdf2image` (requires poppler). Images are stored in `output_images/{pdf_name}/`. Checks for existing images first so reruns are fast.

### `vision_client.py`
Talks to the vLLM-hosted vision model. Converts local images to base64 and sends them via the OpenAI-compatible chat completions API. The model reads the image and returns the extracted text. Includes `save_extraction()` to persist results as JSON.

### `chunker.py`
Takes the raw extracted text and splits it into chunks using Chonkie's semantic chunking (groups related sentences together, threshold 0.8) with overlap (100 characters of shared context between chunks so meaning isn't lost at boundaries). Each chunk becomes an Agno Document and gets stored in Qdrant.

The Qdrant connection is **lazy** — it's not created when you import the module, only when you actually call `ingest_data_to_store()`. This avoids errors when importing the module in contexts where Qdrant isn't needed. MD5 hashing prevents the same content from being inserted twice.

### `manifest.py`
Thread-safe manifest that tracks extraction and indexing state per PDF in `output_store/manifest.json`. Replaces the old `.ingested.log` / `.failed.log` system. Supports clearing indexed markers for Qdrant wipe recovery.

### `run_pipeline.py`
Orchestrates the two-step pipeline. Pages are extracted in parallel (default 2 workers) using a thread pool. Supports running steps independently via CLI flags.

## RunPod Setup (Vision Model)

The vision model (`Qwen/Qwen3-VL-8B-Instruct`) runs on RunPod via vLLM. You only need this for ingestion — querying uses OpenAI directly.

### 1. Create a pod

- Sign in to RunPod → "Serverless & Pods" → "Pods" → "+ New Pod"
- GPU: L40 / L40s / RTX 3090 / RTX 4090 (depending on budget)
- Template: search for a `vllm` community template or use a CUDA + Python image
- Disk: at least 30–60 GB for the model weights
- Launch the pod

### 2. Connect and install vLLM

Open the pod via Web Terminal, Jupyter, or SSH (RunPod provides the SSH command), then:

```bash
pip install vllm
```

### 3. Serve the model

```bash
vllm serve "Qwen/Qwen3-VL-8B-Instruct" \
    --tensor-parallel-size 4 \
    --host 0.0.0.0 \
    --port 8000 \
    --max-model-len 16384 \
    --gpu-memory-utilization 0.95 \
    --trust-remote-code
```

### 4. Configure the endpoint

Copy the RunPod proxy URL and set it in `.env`:

```
VLLM_API_URL=https://your-pod-id-8000.proxy.runpod.net
```

## Usage

Place PDFs in `document-store/` before running.

```bash
# Full pipeline (extract + index)
python -m production_rag.ingestion_pipeline.run_pipeline

# Extract only (no Qdrant)
python -m production_rag.ingestion_pipeline.run_pipeline --step extract

# Index only (from cached JSONs)
python -m production_rag.ingestion_pipeline.run_pipeline --step index

# Re-index after Qdrant wipe
python -m production_rag.ingestion_pipeline.run_pipeline --clear-indexed
python -m production_rag.ingestion_pipeline.run_pipeline --step index
```

Already-extracted pages are skipped automatically. Failed pages are retried on the next extraction run.
