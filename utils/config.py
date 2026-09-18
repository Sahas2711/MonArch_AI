import os
import sys
import time
from dotenv import load_dotenv
from utils.logger import log

load_dotenv()

_secrets_cache = {}
_cache_ttl_seconds = 300


def get_secret(secret_name: str, fallback_env_var: str) -> str:
    """
    Fetch secret from AWS Secrets Manager with 5-minute TTL cache,
    falling back to local environment variable if AWS is not configured.
    """
    now = time.time()
    if secret_name in _secrets_cache:
        val, fetched_at = _secrets_cache[secret_name]
        if now - fetched_at < _cache_ttl_seconds:
            return val

    secret_arn = os.getenv("AWS_SECRET_ARN") or os.getenv("SECRETS_MANAGER_SECRET_ID")
    if secret_arn:
        try:
            import json
            import boto3

            client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
            res = client.get_secret_value(SecretId=secret_arn)
            if "SecretString" in res:
                secrets_dict = json.loads(res["SecretString"])
                if secret_name in secrets_dict:
                    val = secrets_dict[secret_name]
                    _secrets_cache[secret_name] = (val, now)
                    return val
        except Exception as exc:
            log.warning("Secrets Manager fetch failed for %s (%s). Using env fallback.", secret_name, exc)

    val = os.getenv(fallback_env_var, "")
    _secrets_cache[secret_name] = (val, now)
    return val


GROQ_API_KEY = get_secret("GROQ_API_KEY", "GROQ_API_KEY")
RAW_GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
UNSTRUCTURED_API_KEY = get_secret("UNSTRUCTURED_API_KEY", "UNSTRUCTURED_API_KEY")

BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
USE_BEDROCK = os.getenv("USE_BEDROCK", "false").lower() == "true"

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


def _resolve_model(requested_model: str, api_key: str) -> str:
    """Validate requested model against Groq's active catalog and auto-fallback if deprecated."""
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        available = {m.id for m in client.models.list().data}
        if requested_model in available:
            return requested_model

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
            return chosen
    except Exception as exc:
        log.warning("Could not query Groq models (%s); proceeding with '%s'", exc, requested_model)
    return requested_model


def _initialize_llm():
    """Primary LLM initialization: tries Amazon Bedrock first, falling back to Groq."""
    if USE_BEDROCK or os.getenv("AWS_ACCESS_KEY_ID"):
        try:
            from langchain_aws import ChatBedrockConverse
            bedrock_llm = ChatBedrockConverse(
                model=BEDROCK_MODEL_ID,
                region_name=AWS_REGION,
                temperature=0.1,
            )
            log.info("Initialized Amazon Bedrock primary LLM path with model: %s", BEDROCK_MODEL_ID)
            return bedrock_llm, BEDROCK_MODEL_ID
        except Exception as exc:
            log.warning("Failed to initialize Amazon Bedrock (%s); falling back to Groq.", exc)

    if GROQ_API_KEY:
        from langchain_groq import ChatGroq
        groq_model = _resolve_model(RAW_GROQ_MODEL, GROQ_API_KEY)
        groq_llm = ChatGroq(model=groq_model, api_key=GROQ_API_KEY, timeout=30, max_retries=0)
        log.info("Initialized Groq LLM path with model: %s", groq_model)
        return groq_llm, groq_model

    raise RuntimeError("Neither Bedrock nor Groq API key is available for LLM initialization.")


llm, ACTIVE_MODEL_NAME = _initialize_llm()
GROQ_MODEL = ACTIVE_MODEL_NAME
