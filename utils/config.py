import os
import sys
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from utils.logger import log

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RAW_GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY")

# LangSmith Observability setup
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT") or os.getenv("LANGSMITH_PROJECT") or "Monarch"

if LANGCHAIN_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
    os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGSMITH_API_KEY"] = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT
    os.environ["LANGSMITH_PROJECT"] = LANGCHAIN_PROJECT
    log.info("LangSmith observability ACTIVE on project: '%s'", LANGCHAIN_PROJECT)
else:
    log.info("LangSmith tracing disabled (LANGCHAIN_API_KEY not set).")

if not GROQ_API_KEY:
    log.error("GROQ_API_KEY is not set. Copy .env.example to .env and fill it in.")
    sys.exit(1)


def _resolve_model(requested_model: str, api_key: str) -> str:
    """Validate requested model against Groq's active catalog and auto-fallback if deprecated."""
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        available = {m.id for m in client.models.list().data}
        if requested_model in available:
            return requested_model

        # Priority order for replacements
        preferred = [
            "openai/gpt-oss-20b",
            "openai/gpt-oss-120b",
            "qwen/qwen3.6-27b",
            "meta-llama/llama-guard-3-8b",
        ]
        for candidate in preferred:
            if candidate in available:
                log.warning(
                    "Model '%s' is not available on Groq (deprecated or restricted). Auto-switching to '%s'.",
                    requested_model,
                    candidate,
                )
                return candidate

        chat_models = [m for m in available if "whisper" not in m]
        if chat_models:
            chosen = sorted(chat_models)[0]
            log.warning(
                "Model '%s' not available. Selected '%s' from available Groq models: %s",
                requested_model,
                chosen,
                chat_models,
            )
            return chosen
    except Exception as exc:
        log.warning("Could not query Groq models (%s); proceeding with '%s'", exc, requested_model)
    return requested_model


GROQ_MODEL = _resolve_model(RAW_GROQ_MODEL, GROQ_API_KEY)

llm = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, timeout=30, max_retries=0)
