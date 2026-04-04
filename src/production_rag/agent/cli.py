"""Interactive RAG CLI."""

import mlflow

from production_rag.agent.rag_agent import create_rag_agent


def main():
    agent = create_rag_agent()
    print("RAG CLI - Chat with your knowledge base")
    print("Type 'exit' or 'quit' to stop.\n")

    while True:
        try:
            query = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not query:
            continue
        if query.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        agent.print_response(query)

    mlflow.flush_trace_async_logging()


if __name__ == "__main__":
    main()
