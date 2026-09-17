import os
from dotenv import load_dotenv

load_dotenv()

# Embedding model — free, runs locally, no API key needed
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2",  # 384-dim, 22MB, fast
)

# Optional: Unstructured.io API key (for better PDF/DOCX parsing)
# Leave empty to use free local loaders
UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY", "")

# Optional: LLM keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

# Optional: LangChain / LangSmith Observability
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "Monarch")
