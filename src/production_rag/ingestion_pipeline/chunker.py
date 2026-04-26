"""Agno-managed ingestion for raw text into Qdrant."""

import os
from functools import lru_cache
from typing import Optional

from dotenv import find_dotenv, load_dotenv

from agno.db.postgres.postgres import PostgresDb  # optional, but recommended
from agno.knowledge.chunking.fixed import FixedSizeChunking
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.knowledge.knowledge import Knowledge
from agno.knowledge.reader.text_reader import TextReader
from agno.vectordb.qdrant import Qdrant

from production_rag.ingestion_pipeline.config.config_loader import embedder

load_dotenv(find_dotenv())

QDRANT_URL = os.environ["QDRANT_URL"]
QDRANT_API_KEY = os.environ["QDRANT_API_KEY"]
COLLECTION_NAME = os.environ["COLLECTION_NAME"]

_SYNC_DB_URL = os.environ["DATABASE_URL"].replace("+psycopg_async", "+psycopg")


@lru_cache(maxsize=1)
def get_embedder() -> FastEmbedEmbedder:
    return FastEmbedEmbedder(
        id=embedder["model_id"],
        dimensions=embedder["dimensions"],
    )


@lru_cache(maxsize=1)
def _get_reader() -> TextReader:
    """Cached TextReader with fixed-size chunking. Built once per process."""
    return TextReader(
        chunking_strategy=FixedSizeChunking(chunk_size=1500, overlap=200),
    )


@lru_cache(maxsize=1)
def get_knowledge() -> Knowledge:
    emb = get_embedder()

    vector_db = Qdrant(
        collection=COLLECTION_NAME,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        embedder=emb,
    )

    contents_db = None
    if _SYNC_DB_URL:
        contents_db = PostgresDb(
            db_url=_SYNC_DB_URL,
            db_schema="bog_rag",
        )

    return Knowledge(
        name=COLLECTION_NAME,
        description=f"Managed ingestion for {COLLECTION_NAME}",
        vector_db=vector_db,
        contents_db=contents_db,
    )


def ingest_data_to_store(
    text: str,
    meta_data: Optional[dict] = None,
    content_name: Optional[str] = None,
) -> None:
    """
    Agno-managed ingestion:
    - uses Knowledge.insert(...)
    - uses TextReader + SemanticChunking
    - uses the same embedder for chunking and vector storage
    """
    metadata = {"source": COLLECTION_NAME}
    if meta_data:
        metadata.update(meta_data)

    knowledge = get_knowledge()

    knowledge.insert(
        name=content_name or COLLECTION_NAME,
        text_content=text,
        metadata=metadata,
        reader=_get_reader(),
    )


