"""Chunking + Qdrant storage. Lazy connection — no import-time side effects."""

import hashlib
import os

from agno.knowledge.document.base import Document
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.vectordb.qdrant import Qdrant
from chonkie import Pipeline
from dotenv import load_dotenv, find_dotenv

from production_rag.ingestion_pipeline.config.config_loader import embedder

load_dotenv(find_dotenv())

qdrant_url = os.environ["QDRANT_URL"]
qdrant_api_key = os.environ["QDRANT_API_KEY"]
collection_name = os.environ["COLLECTION_NAME"]

_vector_db = None


def _get_vector_db() -> Qdrant:
    global _vector_db
    if _vector_db is None:
        _embedder = FastEmbedEmbedder(
            id=embedder["model_id"], dimensions=embedder["dimensions"]
        )
        _vector_db = Qdrant(
            collection=collection_name,
            url=qdrant_url,
            api_key=qdrant_api_key,
            embedder=_embedder,
        )
        _vector_db.create()
    return _vector_db


def ingest_data_to_store(
    text: str, meta_data: dict = None
) -> int:
    """Chunk text and store in Qdrant. Returns the number of chunks ingested."""
    print(f"Indexing in Qdrant store in collection: {collection_name}")

    base_meta = {"source": collection_name}
    if meta_data:
        base_meta.update(meta_data)

    result = (
        Pipeline()
        .process_with("text")
        .chunk_with("semantic", threshold=0.6)
        .refine_with("overlap", context_size=300)
        .run(texts=text)
    )

    documents = [
        Document(
            content=chunk.text,
            name=collection_name,
            meta_data=base_meta.copy(),
        )
        for chunk in result.chunks
    ]

    content_hash = hashlib.md5(text.encode()).hexdigest()
    _get_vector_db().insert(content_hash=content_hash, documents=documents)
    print(f"Ingested {len(documents)} chunks")
    return len(documents)
