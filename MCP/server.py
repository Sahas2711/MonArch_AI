# MCP/server.py — FastMCP server exposing MonArch AI tools over Streamable-HTTP
from fastmcp import FastMCP
from utils.config import MCP_HOST, MCP_PORT
from utils.logger import log


def run_mcp_server(host: str = MCP_HOST, port: int = MCP_PORT):
    """Start the MonArch MCP server exposing tools over Streamable-HTTP."""

    mcp = FastMCP("MonArch AI Tools")

    # ── Tool 1: RAG Retrieval ──────────────────────────────────────
    @mcp.tool
    def retrieve_documents(query: str, user_id: str = "") -> str:
        """
        Search ingested documents using hybrid RAG (FAISS semantic + BM25 keyword + RRF fusion).
        Returns the top-5 most relevant text chunks as context.
        Use this when you need to find information from previously uploaded documents.
        """
        try:
            from RAG.manager import rag_manager

            result = rag_manager.retrieve(query, user_id=user_id or None)
            return result if result else "(no relevant context found)"
        except Exception as e:
            return f"Error retrieving documents: {e}"

    # ── Tool 2: Document Ingestion ─────────────────────────────────
    @mcp.tool
    def ingest_document(file_path: str, user_id: str = "") -> str:
        """
        Ingest a document file into the RAG vector store.
        Supports: PDF, DOCX, TXT, PNG/JPG (OCR), and other text files.
        The file is chunked, embedded, and indexed for future retrieval.
        Provide the absolute file path on the server's filesystem.
        """
        try:
            import os

            if not os.path.exists(file_path):
                return f"Error: file not found at '{file_path}'"
            from RAG.manager import rag_manager

            result = rag_manager.ingest(file_path, user_id=user_id or None)
            chunks = result.get("chunks_added", 0)
            return f"Successfully ingested '{os.path.basename(file_path)}': {chunks} chunks indexed."
        except Exception as e:
            return f"Error ingesting document: {e}"

    # ── Tool 3: Web Search ─────────────────────────────────────────
    @mcp.tool
    def web_search(query: str) -> str:
        """
        Search the web using DuckDuckGo and return the top 5 results.
        Each result includes the title, snippet, and URL.
        Use this for real-time information not available in ingested documents.
        """
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    results.append(f"• {r['title']}\n  {r['body']}\n  {r['href']}")
            return "\n\n".join(results) if results else "No results found."
        except Exception as e:
            return f"Error performing web search: {e}"

    # ── Tool 4: Calculator ─────────────────────────────────────────
    @mcp.tool
    def calculator(expression: str) -> str:
        """
        Safely evaluate a basic math expression.
        Supports: +, -, *, /, parentheses, and decimal numbers.
        Example: '2 + 2 * 10' → '22'
        """
        try:
            allowed = set("0123456789+-*/.() ")
            if not all(c in allowed for c in expression):
                return "Error: only basic math operators (+, -, *, /, parentheses) are allowed."
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Error evaluating expression: {e}"

    # ── Start Server ───────────────────────────────────────────────
    log.info("Starting MonArch MCP server → http://%s:%d/mcp", host, port)
    mcp.run(transport="streamable-http", host=host, port=port)
