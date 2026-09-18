import os
try:
    from langsmith import traceable
except ImportError:
    def traceable(name=None, **kwargs):
        def decorator(func):
            return func
        return decorator if name or kwargs else (lambda f: f)

from utils.logger import log


@traceable(name="run_eval")
def run_eval(final_state: dict):
    """Optional DeepEval scoring hook — evaluates output quality and logs results."""
    if not os.getenv("OPENAI_API_KEY"):
        log.warning("OPENAI_API_KEY not set — skipping DeepEval metrics evaluation.")
        return None

    try:
        from deepeval import evaluate
        from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
        from deepeval.test_case import LLMTestCase

        messages = final_state.get("messages", [])
        if len(messages) < 2:
            log.warning("Not enough messages to evaluate.")
            return None

        context_str = final_state.get("context", "")
        retrieval_context = [context_str] if context_str and context_str != "(no relevant context found)" else ["No context provided."]

        test_case = LLMTestCase(
            input=final_state["user_inp"],
            actual_output=messages[-1].content,
            retrieval_context=retrieval_context,
        )

        results = evaluate(
            test_cases=[test_case],
            metrics=[
                FaithfulnessMetric(threshold=0.7),
                AnswerRelevancyMetric(threshold=0.7),
            ],
            print_results=False,
        )
        return results
    except Exception as exc:
        log.warning("DeepEval evaluation failed (e.g. rate limit / quota check): %s", exc)
        return {"status": "skipped", "reason": str(exc)}
