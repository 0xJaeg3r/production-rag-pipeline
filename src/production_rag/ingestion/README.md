# Ingestion Pipeline

This is the "write" side of the RAG pipeline. It takes PDF documents and turns them into searchable vectors stored in Qdrant.

## Why not just parse the PDF text directly?

Most financial reports have complex tables, charts, footnotes, and multi-column layouts. Standard PDF text extractors (like PyPDF2 or pdfplumber) lose the structure and mix up columns. Instead, we convert each page to an image and send it to a vision model that can "read" the page like a human would — tables, formatting, and all.

## How it works

```
PDF file → pdf_converter.py → page images (PNG)
                                    |
                          vision_client.py → raw text per page
                                    |
                             chunker.py → semantic chunks → Qdrant
```

1. **PDF to images** — Each page becomes a high-resolution PNG. If the images already exist on disk, this step is skipped.

2. **Image to text** — Each image is sent to a Qwen3-VL-8B vision model running on RunPod. The model extracts all the text content, preserving the meaning from tables and charts.

3. **Text to vectors** — The extracted text is split into smaller, semantically meaningful chunks (not just fixed-size splits — related sentences stay together). Each chunk is embedded into a vector and stored in Qdrant for later retrieval.

## Modules

### `pdf_converter.py`
Converts PDF pages to PNG images using `pdf2image` (requires poppler). Checks for existing images first so reruns are fast.

### `vision_client.py`
Talks to the vLLM-hosted vision model. Converts local images to base64 and sends them via the OpenAI-compatible chat completions API. The model reads the image and returns the extracted text.

### `chunker.py`
Takes the raw extracted text and splits it into chunks using Chonkie's semantic chunking (groups related sentences together, threshold 0.8) with overlap (100 characters of shared context between chunks so meaning isn't lost at boundaries). Each chunk becomes an Agno Document and gets stored in Qdrant.

The Qdrant connection is **lazy** — it's not created when you import the module, only when you actually call `ingest_data_to_store()`. This avoids errors when importing the module in contexts where Qdrant isn't needed. MD5 hashing prevents the same content from being inserted twice.

### `run_pipeline.py`
Orchestrates everything. Finds all PDFs in the `pdf-store/` directory, converts them, extracts text, and stores vectors. Pages are processed in parallel (default 2 workers) using a thread pool. Progress is tracked in log files so you can resume if the process is interrupted:
- `.ingested.log` — pages successfully stored (skipped on rerun)
- `.failed.log` — pages that failed (retried on next run)

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

```bash
# Via console script
rag-ingest

# Via module
python -m production_rag.ingestion.run_pipeline
```

Place PDFs in `src/pdf-store/` before running. Already-ingested pages are skipped automatically.
