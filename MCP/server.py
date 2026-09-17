from utils.config import MCP_HOST, MCP_PORT
from utils.logger import log


def run_mcp_server():
    """Start the MCP (Model Context Protocol) server."""
    try:
        from fastmcp import FastMCP

        mcp = FastMCP("MonArch MCP Server")

        @mcp.tool()
        def query_rag(query: str, user_id: str = None) -> str:
            """Query the RAG vector store for relevant document context."""
            from RAG.manager import rag_manager
            return rag_manager.retrieve(query=query, user_id=user_id)

        @mcp.tool()
        def ingest_document(file_path: str, user_id: str = None) -> str:
            """Ingest a document into the RAG vector store."""
            from RAG.manager import rag_manager
            result = rag_manager.ingest(file_path=file_path, user_id=user_id)
            return f"Ingested {result.get('chunks_added', 0)} chunks successfully."

        log.info("Starting MCP server on %s:%d", MCP_HOST, MCP_PORT)
        mcp.run(transport="sse", host=MCP_HOST, port=MCP_PORT)

    except ImportError:
        log.error("fastmcp is not installed. Run: pip install fastmcp")
    except Exception as exc:
        log.error("MCP server failed: %s", exc)
