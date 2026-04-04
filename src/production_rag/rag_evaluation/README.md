# Evaluation

How do you know if your RAG pipeline is actually working well? You can't just eyeball answers — you need automated, repeatable measurement. This module runs a set of questions with known correct answers through the pipeline and scores the results using RAGAS.

## Why evaluate?

A RAG pipeline can fail in several ways:
- The right documents weren't retrieved (retrieval problem)
- The right documents were retrieved but buried under irrelevant ones (ranking problem)
- The LLM ignored the context and made something up (faithfulness problem)
- The answer is correct but doesn't address the actual question (relevance problem)

Each failure mode needs a different fix. RAGAS scorers tell you exactly which part is breaking.

## How it works

```
eval_questions.json → run each question through the agent → capture traces
    → attach the known correct answer to each trace
    → run RAGAS scorers against the traces
    → results appear in MLflow UI → Evaluations tab
```

1. Load questions and correct answers from `data/eval_questions.json`
2. For each question:
   - Retrieve documents from Qdrant (in a separate retriever span so RAGAS can see what was retrieved)
   - Run the agent to generate an answer
   - Attach the correct answer to the trace via `mlflow.log_expectation()`
   - Save the full trace
3. Pass all traces to `mlflow.genai.evaluate()` with RAGAS scorers
4. View results in the MLflow UI under the Evaluations tab

## What the scorers measure

| Scorer | Question it answers | Needs a correct answer? |
|--------|-------------------|------------------------|
| **Faithfulness** | Did the agent only use information from the retrieved context, or did it make things up? | No |
| **Answer Relevancy** | Does the answer actually address the question that was asked? | No |
| **Context Precision** | Were the retrieved chunks relevant, or was there a lot of noise? | Yes |
| **Context Recall** | Did the retrieved chunks contain all the information needed to answer correctly? | Yes |
| **Context Entity Recall** | Do specific entities (names, numbers, dates) from the correct answer appear in the retrieved context? | Yes |

All scorers use `gpt-4o-mini` as the judge — a separate LLM that evaluates the quality of your RAG pipeline's output.

### Reading the scores

- **1.0** = perfect. The retrieval/answer is as good as it can be.
- **0.0** = complete failure. Nothing useful was retrieved or generated.
- In practice, you'll see scores between 0.5 and 1.0. Focus on the lowest scores first — they tell you where to improve.

If **Faithfulness** is low, the LLM is hallucinating. Tighten the system prompt or lower the temperature.
If **Context Recall** is low, the retriever isn't finding the right chunks. Check your chunking strategy or embedding model.
If **Context Precision** is low, too many irrelevant chunks are being retrieved. The reranker may need tuning.

## Eval questions

`data/eval_questions.json` contains 10 question/answer pairs covering a range of difficulty:
- Simple factual lookups (inflation targets, establishment date)
- Table extraction (NPL ratios, transaction volumes)
- Multi-hop reasoning (tracing monetary policy decisions across the year and connecting them to financial statements)
- Accounting restatements (IFRS treatments, restated figures)

### Adding your own questions

Add entries to the JSON array with `"question"` and `"reference"` keys:

```json
{
    "question": "What was the Bank's Medium-Term Inflation Target...?",
    "reference": "The Medium-Term Inflation Target was 8±2%. Actual Headline Inflation was 23.8%."
}
```

The eval script picks up any question with a `"reference"` key and uses it for the reference-based scorers.

## Usage

```bash
# Via console script
rag-eval

# Via module
python -m production_rag.eval.ragas_eval

# With a custom questions file
python -c "from production_rag.eval.ragas_eval import run_evaluation; run_evaluation('path/to/questions.json')"
```

## Implementation notes

- **Autolog is off during eval** — the eval script builds traces manually. Autolog would create duplicate traces that confuse the scorers. See [integrations/README.md](../integrations/README.md) for the full explanation.
- **`log_expectation()` must come before `get_trace()`** — the correct answer is attached to the trace via `log_expectation()`. If you fetch the trace first, it won't include the expected answer and reference scorers will fail.
- **Sequential execution** — scorers run one at a time (`MAX_WORKERS=1`) to avoid rate-limiting the judge LLM.
- **`nest_asyncio`** — applied at module load to prevent event loop errors from httpx cleanup between RAGAS scorer calls.
- **litellm callback clearing** — prevents a race condition where `genai.evaluate()` re-enables autolog internally and hangs the script.
