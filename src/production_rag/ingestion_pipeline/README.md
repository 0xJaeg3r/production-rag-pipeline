# Ingestion Pipeline

This package is the write path for the repository. It converts PDFs into cached page-level JSON extractions and then indexes those extractions into Qdrant through Agno `Knowledge`.

## Current Flow

```text
document-store/*.pdf
  -> pdf_to_images(...)
  -> output_images/<pdf>/*.png
  -> VLLMVisionClient
  -> output_store/<pdf>/page_N.json
  -> ingest_data_to_store(...)
  -> Knowledge.insert(...)
  -> Qdrant + Postgres contents_db
```

The pipeline is still split into two steps:

- `extract`: render PDF pages and send them to the vision endpoint
- `index`: read cached JSON and insert the extracted text into the knowledge base

## Files

### [run_pipeline.py](run_pipeline.py)

This is the current orchestration entrypoint.

It provides:

- `run_extraction(pdf_dir=None)`
- `run_indexing()`
- `run_ingestion(pdf_dir=None)`

Important current behavior:

- source PDFs default to `src/production_rag/ingestion_pipeline/document-store/`
- extraction writes cache files under repo-root `output_store/`
- rendered page images go under repo-root `output_images/`
- extraction uses a thread pool sized by `pipeline.max_workers`
- indexing runs sequentially
- indexing verifies Agno content status in `contents_db` before marking a page as indexed in the manifest
- `--clear-indexed` clears manifest index markers only

Run it with:

```bash
rag-ingest
python -m production_rag.ingestion_pipeline.run_pipeline
python -m production_rag.ingestion_pipeline.run_pipeline --step extract
python -m production_rag.ingestion_pipeline.run_pipeline --step index
python -m production_rag.ingestion_pipeline.run_pipeline --clear-indexed
```

### [manifest.py](manifest.py)

Tracks pipeline state in `output_store/manifest.json`.

Each PDF entry currently records:

- `total_pages`
- `succeeded`
- `failed`
- `indexed`
- `index_failed`

The manifest is thread-safe and writes atomically through a temporary file.

### [chunker.py](chunker.py)

This file now delegates chunking and indexing to Agno-managed ingestion rather than the older custom logic.

Current implementation details:

- embedder: `snowflake/snowflake-arctic-embed-l`
- vector DB: Qdrant
- content DB: sync `PostgresDb`
- reader: `TextReader`
- chunking strategy: `FixedSizeChunking`
- chunk size: `1500`
- overlap: `200`

`ingest_data_to_store(...)` ultimately calls `knowledge.insert(...)`.

### `pdf_ingestion_pipeline/`

Current helper modules:

- `pdf_to_image_converter.py` for `pdf2image` rendering
- `vision_client.py` for calls to the vLLM vision endpoint and saving extraction JSON
- `image_to_base_64.py` for image payload encoding

## Configuration

`config/config.yaml` currently contains:

```yaml
embedder:
  model_id: "snowflake/snowflake-arctic-embed-l"
  dimensions: 1024

vision:
  model: "Qwen/Qwen3-VL-8B-Instruct"
  prompt: "Extract all the information from the image in paragraph manner. No markdown or No markup or no bullet points."

pipeline:
  max_workers: 2
  output_store: "output_store"
  output_images: "output_images"
```

## Environment Requirements

The current ingestion code expects:

```dotenv
QDRANT_URL=...
QDRANT_API_KEY=...
COLLECTION_NAME=...
DATABASE_URL=postgresql+psycopg_async://user:password@host:5432/dbname
VLLM_API_URL=...
```

Notes:

- `DATABASE_URL` is required even for indexing because `chunker.py` derives a sync Postgres connection string from it.
- `pdf2image` also requires Poppler on the host system.

## Operational Notes

- Extraction is cache-aware. Pages already present in `manifest.succeeded` are skipped.
- Indexing is also cache-aware. Pages already in `manifest.indexed` are skipped.
- Extraction remains parallel, but indexing is intentionally single-threaded because the sync Agno `Knowledge`/`PostgresDb` ingestion path is not safe to hit concurrently from multiple indexing workers.
- If Agno reports a page as `FAILED` in `contents_db`, `run_indexing()` re-opens that page in the manifest and retries it.
- Re-indexing after a Qdrant wipe is handled by clearing manifest index markers and re-running the `index` step.

The older docs mentioned `.ingested.log` and `.failed.log`. The current code no longer uses those files; `output_store/manifest.json` is the source of truth.
