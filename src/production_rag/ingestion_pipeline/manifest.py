"""Thread-safe manifest for tracking PDF extraction and indexing state."""

import json
import os
import threading
from pathlib import Path


class Manifest:
    """Tracks which pages have been extracted and indexed per PDF.

    Backed by manifest.json inside the output store directory.
    All mutations acquire a lock and flush to disk atomically.
    """

    def __init__(self, store_path: Path):
        self._path = store_path / "manifest.json"
        self._lock = threading.Lock()
        self._data = self._load()

    # --- reading ---

    def get_entry(self, pdf_name: str) -> dict | None:
        return self._data.get(pdf_name)

    def succeeded_pages(self, pdf_name: str) -> set[int]:
        entry = self._data.get(pdf_name, {})
        return set(entry.get("succeeded", []))

    def failed_pages(self, pdf_name: str) -> set[int]:
        entry = self._data.get(pdf_name, {})
        return set(entry.get("failed", []))

    def indexed_pages(self, pdf_name: str) -> set[int]:
        entry = self._data.get(pdf_name, {})
        return set(entry.get("indexed", []))

    def pages_needing_extraction(self, pdf_name: str, total_pages: int) -> list[int]:
        """Pages that have not been successfully extracted yet."""
        succeeded = self.succeeded_pages(pdf_name)
        return sorted(p for p in range(1, total_pages + 1) if p not in succeeded)

    def pages_needing_indexing(self, pdf_name: str) -> list[int]:
        """Succeeded pages not yet indexed into Qdrant."""
        succeeded = self.succeeded_pages(pdf_name)
        indexed = self.indexed_pages(pdf_name)
        return sorted(succeeded - indexed)

    def all_pdfs(self) -> list[str]:
        return list(self._data.keys())

    # --- writing ---

    def register_pdf(self, pdf_name: str, total_pages: int) -> None:
        with self._lock:
            if pdf_name not in self._data:
                self._data[pdf_name] = {
                    "total_pages": total_pages,
                    "succeeded": [],
                    "failed": [],
                    "indexed": [],
                }
            else:
                self._data[pdf_name]["total_pages"] = total_pages
            self._flush()

    def mark_succeeded(self, pdf_name: str, page_number: int) -> None:
        with self._lock:
            entry = self._data[pdf_name]
            if page_number not in entry["succeeded"]:
                entry["succeeded"].append(page_number)
                entry["succeeded"].sort()
            if page_number in entry["failed"]:
                entry["failed"].remove(page_number)
            self._flush()

    def mark_failed(self, pdf_name: str, page_number: int) -> None:
        with self._lock:
            entry = self._data[pdf_name]
            if page_number not in entry["failed"]:
                entry["failed"].append(page_number)
                entry["failed"].sort()
            self._flush()

    def mark_indexed(self, pdf_name: str, page_number: int) -> None:
        with self._lock:
            entry = self._data[pdf_name]
            if page_number not in entry["indexed"]:
                entry["indexed"].append(page_number)
                entry["indexed"].sort()
            self._flush()

    def clear_indexed(self, pdf_name: str | None = None) -> None:
        """Clear indexed list for one PDF, or all PDFs."""
        with self._lock:
            if pdf_name:
                if pdf_name in self._data:
                    self._data[pdf_name]["indexed"] = []
            else:
                for entry in self._data.values():
                    entry["indexed"] = []
            self._flush()

    # --- internal ---

    def _flush(self) -> None:
        tmp = self._path.with_suffix(".json.tmp")
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self._path)

    def _load(self) -> dict:
        if self._path.exists():
            content = self._path.read_text().strip()
            if content:
                return json.loads(content)
        return {}
