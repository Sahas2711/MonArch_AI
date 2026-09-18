import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

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
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Optional: LangChain / LangSmith Observability
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "Monarch")

# MCP Server
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))

# Validate required API key at startup
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY is required. Set it in your .env file or environment. "
        "Get a key at https://console.groq.com/keys"
    )

# LLM instance
llm = ChatGroq(model=GROQ_MODEL, api_key=GROQ_API_KEY, timeout=60, max_retries=2)
