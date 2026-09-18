from fastmcp import FastMCP
from Agents.research import _search_tool
from RAG.manager import rag_manager
from utils.logger import log


def run_mcp_server():
    """Start FastMCP server exposing Monarch RAG and search tools over streamable-http."""
    mcp_server = FastMCP("Monarch tools")

    @mcp_server.tool
    def retriever_tool(query: str, user_id: str = "") -> str:
        """Retrieve relevant document context for a query."""
        return rag_manager.retrieve(query, user_id=user_id or None)

    @mcp_server.tool
    def websearch_tool(query: str) -> str:
        """Search the web with DuckDuckGo."""
        return _search_tool.invoke(query)

    log.info("Starting MCP server on http://127.0.0.1:8000/mcp (streamable-http)")
    mcp_server.run(transport="streamable-http", host="127.0.0.1", port=8000)
