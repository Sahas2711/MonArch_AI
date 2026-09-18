from fastmcp import FastMCP
from Agents.research import _search_tool
from RAG.manager import rag_manager
from utils.logger import log

# Allowed file extensions for document ingestion
ALLOWED_INGEST_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".doc",
    ".txt",
    ".md",
    ".csv",
    ".log",
    ".png",
    ".jpg",
    ".jpeg",
    ".json",
}
MAX_INGEST_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_QUERY_LENGTH = 4000
MAX_SEARCH_QUERY_LENGTH = 500
MAX_CALCULATOR_EXPR_LENGTH = 200


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
=======
# Safe AST operators for calculator
_MATH_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval_math(expression: str) -> float:
    """Evaluate a mathematical expression safely using AST parsing without calling eval()."""
    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Invalid constant type: {type(node.value).__name__}")
        elif isinstance(node, ast.Num):  # Python < 3.8 compatibility
            return node.n
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _MATH_OPERATORS:
                raise ValueError(f"Unsupported binary operator: {op_type.__name__}")
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
                raise ZeroDivisionError("Division by zero")
            return _MATH_OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _MATH_OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type.__name__}")
            operand = _eval_node(node.operand)
            return _MATH_OPERATORS[op_type](operand)
        else:
            raise ValueError(f"Unsupported syntax: {type(node).__name__}")

    parsed = ast.parse(expression.strip(), mode="eval")
    return _eval_node(parsed)


def create_mcp_server(auth_token: str = MCP_AUTH_TOKEN) -> FastMCP:
    """Construct and configure the FastMCP server instance with all tools and optional authentication."""
    auth_obj = None
    if auth_token:
        try:
            import importlib

            auth_mod = importlib.import_module("fastmcp.auth")
            bearer_cls = getattr(auth_mod, "BearerAuth", None)
            if bearer_cls is not None:
                auth_obj = bearer_cls(token=auth_token)
        except Exception:
            try:
                import fastmcp

                bearer_cls = getattr(fastmcp, "BearerAuth", None)
                if bearer_cls is not None:
                    auth_obj = bearer_cls(token=auth_token)
            except Exception:
                auth_obj = None

        if auth_obj is None:
            log.warning("BearerAuth not available in installed fastmcp version; server will start without auth wrapper.")

    mcp = FastMCP("MonArch AI Tools", auth=auth_obj) if auth_obj else FastMCP("MonArch AI Tools")

    # ── Tool 1: RAG Retrieval ──────────────────────────────────────
    @mcp.tool
    def retrieve_documents(query: str, user_id: str = "") -> str:
        """
        Search ingested documents using hybrid RAG (FAISS semantic + BM25 keyword + RRF fusion).
        Returns the top-5 most relevant text chunks as context.
        Use this when you need to find information from previously uploaded documents.
        """
        try:
            if not query or not query.strip():
                return "Error: query cannot be empty."
            if len(query) > MAX_QUERY_LENGTH:
                return f"Error: query exceeds maximum length of {MAX_QUERY_LENGTH} characters."

            clean_user_id = user_id.strip() if user_id else None
            if clean_user_id and len(clean_user_id) > 128:
                return "Error: user_id exceeds maximum length of 128 characters."

            from RAG.manager import rag_manager

            result = rag_manager.retrieve(query.strip(), user_id=clean_user_id)
            return result if result else "(no relevant context found)"
        except Exception as e:
            log.error("Error retrieving documents: %s", e, exc_info=True)
            return f"Error retrieving documents: {e}"

    # Alias for backwards compatibility with query_rag references
    @mcp.tool(name="query_rag")
    def query_rag(query: str, user_id: str = "") -> str:
        """Alias for retrieve_documents."""
        return retrieve_documents(query=query, user_id=user_id)

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
            if not file_path or not file_path.strip():
                return "Error: file_path cannot be empty."

            cleaned_path = file_path.strip()
            if len(cleaned_path) > 1024:
                return "Error: file_path exceeds maximum length of 1024 characters."

            # Normalize and resolve path to check for path traversal issues
            resolved_path = os.path.abspath(os.path.normpath(cleaned_path))

            if not os.path.exists(resolved_path):
                return f"Error: file not found at '{cleaned_path}'"

            if not os.path.isfile(resolved_path):
                return f"Error: path '{cleaned_path}' is not a regular file."

            # Check file extension whitelist
            _, ext = os.path.splitext(resolved_path)
            if ext.lower() not in ALLOWED_INGEST_EXTENSIONS:
                allowed_str = ", ".join(sorted(ALLOWED_INGEST_EXTENSIONS))
                return f"Error: unsupported file extension '{ext}'. Supported formats: {allowed_str}"

            # Check file size
            file_size = os.path.getsize(resolved_path)
            if file_size > MAX_INGEST_FILE_SIZE:
                return f"Error: file size ({file_size / (1024*1024):.1f}MB) exceeds limit of 50MB."

            clean_user_id = user_id.strip() if user_id else None
            if clean_user_id and len(clean_user_id) > 128:
                return "Error: user_id exceeds maximum length of 128 characters."

            from RAG.manager import rag_manager

            result = rag_manager.ingest(resolved_path, user_id=clean_user_id)
            chunks = result.get("chunks_added", 0)
            return f"Successfully ingested '{os.path.basename(resolved_path)}': {chunks} chunks indexed."
        except Exception as e:
            log.error("Error ingesting document '%s': %s", file_path, e, exc_info=True)
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
            if not query or not query.strip():
                return "Error: search query cannot be empty."
            if len(query) > MAX_SEARCH_QUERY_LENGTH:
                return f"Error: search query exceeds maximum length of {MAX_SEARCH_QUERY_LENGTH} characters."

            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query.strip(), max_results=5):
                    results.append(f"• {r['title']}\n  {r['body']}\n  {r['href']}")
            return "\n\n".join(results) if results else "No results found."
        except Exception as e:
            log.error("Error performing web search for '%s': %s", query, e, exc_info=True)
            return f"Error performing web search: {e}"

    # ── Tool 4: Calculator ─────────────────────────────────────────
    @mcp.tool
    def calculator(expression: str) -> str:
        """
        Safely evaluate a basic math expression.
        Supports: +, -, *, /, //, %, **, parentheses, and decimal numbers.
        Example: '2 + 2 * 10' → '22'
        """
        try:
            if not expression or not expression.strip():
                return "Error: expression cannot be empty."
            if len(expression) > MAX_CALCULATOR_EXPR_LENGTH:
                return f"Error: expression exceeds maximum length of {MAX_CALCULATOR_EXPR_LENGTH} characters."

            allowed_chars = set("0123456789+-*/.() %^")
            if not all(c in allowed_chars for c in expression):
                return "Error: only basic math operators (+, -, *, /, //, %, **, parentheses) are allowed."

            # Use safe AST evaluator (prevents arbitrary code execution)
            result = _safe_eval_math(expression)
            # Format integer outputs without trailing .0
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return str(result)
        except ZeroDivisionError:
            return "Error: division by zero."
        except Exception as e:
            log.error("Error evaluating calculator expression '%s': %s", expression, e, exc_info=True)
            return f"Error evaluating expression: {e}"

    return mcp


def run_mcp_server(
    host: str = MCP_HOST,
    port: int = MCP_PORT,
    auth_token: str = MCP_AUTH_TOKEN,
    **kwargs,
):
    """Start the MonArch MCP server exposing tools over Streamable-HTTP."""
    mcp = create_mcp_server(auth_token=auth_token)
    log.info("Starting MonArch MCP server → http://%s:%d/mcp (transport: streamable-http)", host, port)
    mcp.run(transport="streamable-http", host=host, port=port, **kwargs)
