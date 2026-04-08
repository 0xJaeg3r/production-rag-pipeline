"""Ingestion orchestrator: PDF -> Extract -> Index.

Two decoupled steps:
  1. Extract: PDF -> images -> vision LLM -> cached page JSONs
  2. Index:   cached page JSONs -> chunker -> Qdrant
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pdf2image import pdfinfo_from_path

from production_rag.ingestion_pipeline.manifest import Manifest
from production_rag.ingestion_pipeline.pdf_ingestion_pipeline.pdf_to_image_converter import pdf_to_images
from production_rag.ingestion_pipeline.pdf_ingestion_pipeline.vision_client import VLLMVisionClient
from production_rag.ingestion_pipeline.chunker import ingest_data_to_store
from production_rag.ingestion_pipeline.config.config_loader import (
    max_workers, output_store, output_images, vision_prompt,
)
# from agno.db.sqlite import SqliteDb
from agno.db.postgres import PostgresDb
from agno.knowledge.content import ContentStatus
from agno.db.schemas.knowledge import KnowledgeRow
import hashlib
import time
import os

from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

_store_path = Path(output_store)
_images_path = Path(output_images)

_RAG_DIR = Path(os.environ.get("RAG_DATA_DIR", str(Path.home() / ".production-rag")))
_RAG_DIR.mkdir(exist_ok=True)
# _contents_db = SqliteDb(db_file=str(_RAG_DIR / "knowledge_contents.db"))
_sync_db_url = os.environ["DATABASE_URL"].replace("+psycopg_async", "+psycopg")
_contents_db = PostgresDb(db_url=_sync_db_url, db_schema="knowledge")


def _page_json_path(pdf_stem: str, page_num: int) -> Path:
    return _store_path / pdf_stem / f"page_{page_num}.json"


# --- Step 1: Extract ---

def run_extraction(pdf_dir: Path | None = None) -> dict:
    """PDF -> images -> vision LLM -> page JSONs."""
    pdf_dir = pdf_dir or Path(__file__).resolve().parent / "document-store"
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {pdf_dir}")
        return {"extracted": 0, "failed": 0, "skipped": 0}

    _store_path.mkdir(parents=True, exist_ok=True)
    manifest = Manifest(_store_path)
    client = VLLMVisionClient()

    totals = {"extracted": 0, "failed": 0, "skipped": 0}

    for pdf_path in pdf_files:
        pdf_name = pdf_path.name
        pdf_stem = pdf_path.stem
        total_pages = pdfinfo_from_path(str(pdf_path))["Pages"]

        manifest.register_pdf(pdf_name, total_pages)

        print(f"\nConverting: {pdf_name}")
        image_paths = pdf_to_images(str(pdf_path), output_folder=str(_images_path))

        page_to_image = {}
        for img_path in image_paths:
            page_num = int(img_path.rsplit("_page_", 1)[-1].replace(".png", ""))
            page_to_image[page_num] = img_path

        pages_to_extract = manifest.pages_needing_extraction(pdf_name, total_pages)
        skipped = total_pages - len(pages_to_extract)
        totals["skipped"] += skipped

        if not pages_to_extract:
            print(f"All {total_pages} pages already extracted for {pdf_name}")
            continue

        print(f"Extracting {len(pages_to_extract)} pages ({skipped} skipped)")

        def _extract_page(page_num, _pdf_name=pdf_name, _pdf_stem=pdf_stem):
            image_path = page_to_image.get(page_num)
            if not image_path:
                print(f"No image found for {_pdf_name} page {page_num}")
                manifest.mark_failed(_pdf_name, page_num)
                return False

            print(f"\nExtracting: {_pdf_name} page {page_num}")
            response = client.chat_with_local_image(vision_prompt, image_path)
            text = client.extract_response_text(response) if response else None

            if not text:
                print(f"No text extracted from {_pdf_name} page {page_num}")
                manifest.mark_failed(_pdf_name, page_num)
                return False

            client.save_extraction(
                text=text,
                output_path=_page_json_path(_pdf_stem, page_num),
                source_file=_pdf_name,
                page_number=page_num,
            )
            manifest.mark_succeeded(_pdf_name, page_num)
            return True

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(_extract_page, p): p
                for p in pages_to_extract
            }
            for future in as_completed(futures):
                if future.result():
                    totals["extracted"] += 1
                else:
                    totals["failed"] += 1

    print(f"\nExtraction complete: {totals}")
    return totals


# --- Step 2: Index ---

def run_indexing() -> dict:
    """Read cached page JSONs -> chunker -> Qdrant."""
    manifest = Manifest(_store_path)
    totals = {"indexed": 0, "skipped": 0, "failed": 0}

    for pdf_name in manifest.all_pdfs():
        pdf_stem = Path(pdf_name).stem
        pages_to_index = manifest.pages_needing_indexing(pdf_name)
        skipped = len(manifest.indexed_pages(pdf_name))
        totals["skipped"] += skipped

        if not pages_to_index:
            print(f"All pages already indexed for {pdf_name}")
            continue

        print(f"\nIndexing {len(pages_to_index)} pages for {pdf_name} ({skipped} skipped)")

        for page_num in pages_to_index:
            json_path = _page_json_path(pdf_stem, page_num)
            if not json_path.exists():
                print(f"Missing JSON for {pdf_name} page {page_num}")
                totals["failed"] += 1
                continue

            with open(json_path) as f:
                page_data = json.load(f)

            try:
                meta = {
                    "source_file": page_data["source_file"],
                    "page_number": page_data["page_number"],
                }
                ingest_data_to_store(
                    text=page_data["text"],
                    meta_data=meta,
                )
                content_hash = hashlib.md5(
                    f"{pdf_name}_page_{page_num}".encode()
                ).hexdigest()
                now = int(time.time())
                _contents_db.upsert_knowledge_content(
                    knowledge_row=KnowledgeRow(
                        id=content_hash,
                        name=f"{pdf_name}_page_{page_num}",
                        description="",
                        metadata=meta,
                        type="Text",
                        size=len(page_data["text"]),
                        linked_to="",
                        access_count=0,
                        status=ContentStatus.COMPLETED,
                        status_message="",
                        created_at=now,
                        updated_at=now,
                    )
                )
                manifest.mark_indexed(pdf_name, page_num)
                totals["indexed"] += 1
            except Exception as e:
                print(f"Error indexing {pdf_name} page {page_num}: {e}")
                totals["failed"] += 1

    print(f"\nIndexing complete: {totals}")
    return totals


# --- Full pipeline ---

def run_ingestion(pdf_dir=None) -> dict:
    """Run both steps: extract then index."""
    extract_result = run_extraction(Path(pdf_dir) if pdf_dir else None)
    index_result = run_indexing()
    return {
        "extracted": extract_result["extracted"],
        "indexed": index_result["indexed"],
        "failed": extract_result["failed"] + index_result["failed"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF ingestion pipeline")
    parser.add_argument(
        "--step", choices=["extract", "index", "both"], default="both",
        help="Which pipeline step to run",
    )
    parser.add_argument(
        "--clear-indexed", action="store_true",
        help="Clear all indexed markers (for Qdrant wipe recovery)",
    )
    args = parser.parse_args()

    if args.clear_indexed:
        _store_path.mkdir(parents=True, exist_ok=True)
        Manifest(_store_path).clear_indexed()
        print("Cleared all indexed markers.")

    if args.step == "extract":
        run_extraction()
    elif args.step == "index":
        run_indexing()
    else:
        run_ingestion()
