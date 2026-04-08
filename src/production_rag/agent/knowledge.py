"""Knowledge base factory."""

from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.knowledge.reranker.cohere import CohereReranker
from agno.vectordb.qdrant import Qdrant
from agno.db.sqlite import SqliteDb
from agno.db.postgres import AsyncPostgresDb
from pathlib import Path

import os

from dotenv import load_dotenv, find_dotenv

from production_rag.agent.config.config_loader import embedder, reranker

load_dotenv(find_dotenv())

qdrant_url = os.environ["QDRANT_URL"]
qdrant_api_key = os.environ["QDRANT_API_KEY"]
collection_name = os.environ["COLLECTION_NAME"]

RAG_DIR = Path(os.environ["RAG_DATA_DIR"])
RAG_DIR.mkdir(exist_ok=True)


def create_knowledge_base() -> Knowledge:
    """Build embedder, reranker, Qdrant, and Knowledge from config."""
    _embedder = FastEmbedEmbedder(
        id=embedder["model_id"], dimensions=embedder["dimensions"]
    )
    _reranker = CohereReranker(model=reranker["model"], top_n=reranker["top_n"])

    vector_db = Qdrant(
        collection=collection_name,
        url=qdrant_url,
        api_key=qdrant_api_key,
        embedder=_embedder,
        reranker=_reranker,
    )

    # contents_db = SqliteDb(db_file=str(RAG_DIR / "knowledge_contents.db"))
    contents_db = AsyncPostgresDb(db_url=os.environ["DATABASE_URL"], db_schema="knowledge")

    return Knowledge(vector_db=vector_db, contents_db=contents_db, max_results=40)
