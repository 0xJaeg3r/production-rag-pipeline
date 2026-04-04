"""Batch evaluation of the RAG agent using MLflow + RAGAS scorers.

Run:
    python -m production_rag.eval.ragas_eval
"""

import json
import os
from pathlib import Path

import nest_asyncio

nest_asyncio.apply()

import litellm
import mlflow
import pandas as pd
from mlflow.entities import AssessmentSource, AssessmentSourceType, SpanType
from mlflow.entities import Document as MLflowDocument
from mlflow.genai.scorers.ragas import (
    AnswerRelevancy,
    ContextEntityRecall,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from production_rag.agent.rag_agent import create_rag_agent
from production_rag.integrations.mlflow import setup_mlflow
from production_rag.rag_evaluation.config.config_loader import judge_model

DEFAULT_QUESTIONS_PATH = Path(__file__).resolve().parent / "eval_questions.json"


def run_evaluation(questions_path=None):
    questions_path = Path(questions_path or DEFAULT_QUESTIONS_PATH)
    with open(questions_path) as f:
        eval_questions = json.load(f)

    setup_mlflow(autolog=False)
    agent = create_rag_agent(autolog=False)
    traces = []

    @mlflow.trace(span_type=SpanType.RETRIEVER)
    def retrieve_docs(query: str):
        docs = agent.knowledge.vector_db.search(query=query, limit=10)
        return [
            MLflowDocument(
                page_content=doc.content if hasattr(doc, "content") else str(doc),
                metadata={"doc_uri": doc.name if hasattr(doc, "name") else ""},
            )
            for doc in docs
        ]

    @mlflow.trace
    def rag_pipeline(question: str) -> str:
        retrieve_docs(question)
        response = agent.run(question, stream=False)
        return response.content or ""

    for i, item in enumerate(eval_questions, 1):
        question = item["question"]
        print(f"[{i}/{len(eval_questions)}] {question[:80]}...")

        rag_pipeline(question)
        trace_id = mlflow.get_last_active_trace_id()

        if "reference" in item:
            mlflow.log_expectation(
                trace_id=trace_id,
                name="expected_output",
                value=item["reference"],
                source=AssessmentSource(
                    source_type=AssessmentSourceType.HUMAN,
                    source_id="ground_truth",
                ),
            )

        trace = mlflow.get_trace(trace_id)
        traces.append(trace)
        n_docs = sum(
            1
            for s in trace.data.spans
            if s.span_type == "RETRIEVER"
            for _ in (s.outputs if isinstance(s.outputs, list) else [])
        )
        print(f"  {n_docs} docs in retriever span, trace built.\n")

    print("Running RAGAS evaluation...\n")

    scorers = [
        Faithfulness(model=judge_model),
        AnswerRelevancy(model=judge_model),
        ContextPrecision(model=judge_model),
        ContextRecall(model=judge_model),
        ContextEntityRecall(model=judge_model),
    ]

    os.environ["MLFLOW_GENAI_EVAL_MAX_WORKERS"] = "1"
    os.environ["MLFLOW_GENAI_EVAL_MAX_SCORER_WORKERS"] = "1"

    mlflow.autolog(disable=True)
    litellm.callbacks = []
    litellm.success_callback = []
    litellm.failure_callback = []
    litellm._async_success_callback = []
    litellm._async_failure_callback = []

    eval_df = pd.DataFrame({"trace": traces})
    results = mlflow.genai.evaluate(data=eval_df, scorers=scorers)

    print("\n=== RAGAS Evaluation Results ===")
    print(results.result_df.to_string(index=False))
    print("\nFull results logged to MLflow UI → Evaluations tab")


if __name__ == "__main__":
    run_evaluation()
