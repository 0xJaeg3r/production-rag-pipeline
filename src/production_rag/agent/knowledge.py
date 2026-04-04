"""Knowledge base factory."""

from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.knowledge.reranker.cohere import CohereReranker
from agno.vectordb.qdrant import Qdrant

import os

from dotenv import load_dotenv, find_dotenv

from production_rag.agent.config.config_loader import embedder, reranker

load_dotenv(find_dotenv())

qdrant_url = os.environ["QDRANT_URL"]
qdrant_api_key = os.environ["QDRANT_API_KEY"]
collection_name = os.environ["COLLECTION_NAME"]


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

    return Knowledge(vector_db=vector_db, max_results=10)
