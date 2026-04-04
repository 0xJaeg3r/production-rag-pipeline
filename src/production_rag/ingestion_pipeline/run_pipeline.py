"""Ingestion orchestrator: PDF → Images → Vision LLM → Qdrant."""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from production_rag.ingestion_pipeline.pdf_converter import pdf_to_images
from production_rag.ingestion_pipeline.vision_client import VLLMVisionClient
from production_rag.ingestion_pipeline.chunker import ingest_data_to_store


def run_ingestion(pdf_dir="src/pdf-store", output_dir="output_images", max_workers=2):
    """Run the full ingestion pipeline. Returns dict with ingested/failed counts."""
    pdf_store = Path(pdf_dir)
    pdf_files = list(pdf_store.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDFs found in {pdf_store}")
        return {"ingested": 0, "failed": 0}

    # Tracking logs
    ingested_log = Path(output_dir) / ".ingested.log"
    failed_log = Path(output_dir) / ".failed.log"

    ingested = set()
    if ingested_log.exists():
        ingested = set(ingested_log.read_text().strip().splitlines())
    if failed_log.exists():
        failed_log.unlink()

    client = VLLMVisionClient()
    failed_pages = []
    log_lock = threading.Lock()

    def process_page(image_path, page_num, pdf_name):
        print(f"\nProcessing: {image_path}")
        try:
            response = client.chat_with_local_image(
                text_prompt="Extract all the information from the image in paragraph manner. No markdown or No markup or no bullet points.",
                image_path=image_path,
            )

            if response:
                text_response = client.extract_response_text(response)
                if text_response:
                    ingest_data_to_store(
                        text_response,
                        meta_data={
                            "source_file": pdf_name,
                            "page_number": page_num,
                        },
                    )
                    with log_lock:
                        with open(ingested_log, "a") as f:
                            f.write(f"{image_path}\n")
                    return None
                else:
                    print(f"No text extracted from {image_path}")
                    return image_path
            else:
                print(f"No response from vision model for {image_path}")
                return image_path
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            return image_path

    for pdf_path in pdf_files:
        print(f"\nConverting: {pdf_path.name}")
        image_paths = pdf_to_images(str(pdf_path), output_folder=output_dir)

        pages_to_process = []
        for image_path in image_paths:
            if image_path in ingested:
                print(f"\nSkipping (already ingested): {image_path}")
                continue
            page_num = int(image_path.rsplit("_page_", 1)[-1].replace(".png", ""))
            pages_to_process.append((image_path, page_num, pdf_path.name))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_page, img, num, name): img
                for img, num, name in pages_to_process
            }
            for future in as_completed(futures):
                failed = future.result()
                if failed:
                    failed_pages.append(failed)

    if failed_pages:
        with open(failed_log, "w") as f:
            for page in failed_pages:
                f.write(f"{page}\n")
        print(f"\nFailed pages ({len(failed_pages)}) — see {failed_log}:")
        for page in failed_pages:
            print(f"  - {page}")

    total_ingested = len(pages_to_process) - len(failed_pages)
    return {"ingested": total_ingested, "failed": len(failed_pages)}


if __name__ == "__main__":
    run_ingestion()
