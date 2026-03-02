"""Knowledge base factory."""

from agno.knowledge.knowledge import Knowledge
from agno.knowledge.embedder.fastembed import FastEmbedEmbedder
from agno.knowledge.reranker.cohere import CohereReranker
from agno.vectordb.qdrant import Qdrant

from production_rag.config import (
    qdrant as qdrant_cfg,
    embedder as embedder_cfg,
    reranker as reranker_cfg,
)


def create_knowledge_base() -> Knowledge:
    """Build embedder, reranker, Qdrant, and Knowledge from config."""
    _embedder = FastEmbedEmbedder(
        id=embedder_cfg.model_id, dimensions=embedder_cfg.dimensions
    )
    _reranker = CohereReranker(model=reranker_cfg.model, top_n=reranker_cfg.top_n)

    vector_db = Qdrant(
        collection=qdrant_cfg.collection_name,
        url=qdrant_cfg.url,
        api_key=qdrant_cfg.api_key,
        embedder=_embedder,
        reranker=_reranker,
    )

    return Knowledge(vector_db=vector_db, max_results=10)
