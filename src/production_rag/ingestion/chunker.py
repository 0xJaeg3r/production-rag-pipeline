"""Chunking + Qdrant storage. Lazy connection — no import-time side effects."""

import hashlib

from agno.knowledge.document.base import Document
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.vectordb.qdrant import Qdrant
from chonkie import Pipeline

from production_rag.config import qdrant as qdrant_cfg, embedder as embedder_cfg

_vector_db = None


def _get_vector_db() -> Qdrant:
    global _vector_db
    if _vector_db is None:
        _embedder = FastEmbedEmbedder(
            id=embedder_cfg.model_id, dimensions=embedder_cfg.dimensions
        )
        _vector_db = Qdrant(
            collection=qdrant_cfg.collection_name,
            url=qdrant_cfg.url,
            api_key=qdrant_cfg.api_key,
            embedder=_embedder,
        )
        _vector_db.create()
    return _vector_db


def ingest_data_to_store(
    text: str, source_name: str = None, meta_data: dict = None
) -> int:
    """Chunk text and store in Qdrant. Returns the number of chunks ingested."""
    source_name = source_name or qdrant_cfg.collection_name
    print(f"Indexing in Qdrant store in collection: {qdrant_cfg.collection_name}")

    base_meta = {"source": source_name}
    if meta_data:
        base_meta.update(meta_data)

    result = (
        Pipeline()
        .process_with("text")
        .chunk_with("semantic", threshold=0.8)
        .refine_with("overlap", context_size=100)
        .run(texts=text)
    )

    documents = [
        Document(
            content=chunk.text,
            name=source_name,
            meta_data=base_meta.copy(),
        )
        for chunk in result.chunks
    ]

    content_hash = hashlib.md5(text.encode()).hexdigest()
    _get_vector_db().insert(content_hash=content_hash, documents=documents)
    print(f"Ingested {len(documents)} chunks")
    return len(documents)
