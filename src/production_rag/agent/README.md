# Agent

This is the "read" side of the RAG pipeline. When a user asks a question, the agent retrieves relevant chunks from the vector database, reranks them, and uses an LLM to generate a grounded answer.

## How retrieval and reranking work

When you ask a question, two things happen:

1. **Retrieval** — Your question is converted into a vector (using the same embedding model from ingestion) and compared against all stored vectors in Qdrant. The top 10 most similar chunks are returned. This is fast but approximate — it finds chunks that are semantically close to your question.

2. **Reranking** — The retrieved chunks are passed through a Cohere reranker, which is a separate model trained specifically to score how relevant a document is to a query. It's more accurate than vector similarity alone but slower, so we only run it on the top 10 results and keep the best 5. This two-stage approach (fast retrieval, then precise reranking) gives you both speed and accuracy.

## How the agent generates answers

The agent receives the reranked chunks as context along with your question. It's instructed to only use the provided context (no outside knowledge), cite specific sections, and distinguish between Bank and Group figures. If the context doesn't contain the answer, it says so instead of making something up.

## Modules

### `prompts.py`
Contains the system prompt and a list of 12 instructions that tell the agent how to behave. These are specific to financial analysis of the Bank of Ghana report — you'd modify these for other domains. The instructions cover things like:
- Pay attention to units (millions vs billions, GH¢ vs US$)
- Distinguish between Bank (standalone) and Group (Bank + subsidiaries) figures
- Watch for restated 2023 figures
- Read tables carefully (headers, rows, footnotes)
- Always cite the source section or table

### `knowledge.py`
Builds the knowledge base from config. This wires together the embedder, reranker, and Qdrant connection into a single `Knowledge` object that the agent uses for retrieval.

The embedder model here **must match** the one used during ingestion. Both read from the same `EmbedderConfig` in `config.py`, so they're always in sync.

### `rag_agent.py`
The main entry point. `create_rag_agent()` wires everything together: sets up MLflow tracing, creates the knowledge base, configures the LLM, and returns a ready-to-use Agno `Agent`.

Nothing happens when you import this module — the agent is only created when you call the function. This avoids errors and side effects when importing in different contexts (tests, scripts, etc.).

## Usage

```python
from production_rag.agent.rag_agent import create_rag_agent

agent = create_rag_agent()
agent.print_response("What was the NPL ratio in 2024?")
```
