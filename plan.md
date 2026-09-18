🔌 Adding an MCP Server to a New Repo — From Scratch
🤔 What is MCP?
MCP (Model Context Protocol) is an open standard by Anthropic that lets any AI (Claude, Cursor, Copilot, etc.) call your tools — like your RAG system, database, or web search — as if they were built-in capabilities.

Think of it like a USB-C port for AI tools:

You build a server that exposes tools
Any MCP-compatible AI client plugs into it
The AI can now call your tools by name

Claude Desktop / Cursor / Any MCP Client
          │
          │  "retrieve documents about payment terms"
          ▼
    ┌─────────────┐
    │  MCP Server │   ← your server.py
    │  (FastMCP)  │
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │  Your Tools │
    │  - RAG      │
    │  - Search   │
    │  - DB       │
    └─────────────┘
📁 Files You Need

my-project/
├── MCP/
│   ├── __init__.py     ← empty
│   └── server.py       ← the MCP server
├── RAG/                ← (optional) if you want RAG as a tool
│   └── ...
├── utils/
│   └── logger.py
├── main.py             ← CLI entrypoint
└── requirements.txt
Step 1 — Install FastMCP
Add to requirements.txt:

txt

fastmcp>=2.0.0
duckduckgo-search>=6.0.0    # for web search tool (optional)
Install:

bash

pip install fastmcp duckduckgo-search
Step 2 — Create MCP/__init__.py
python

# MCP/__init__.py
# (empty — just makes it a Python package)
Step 3 — Create MCP/server.py
This is the entire MCP server. Three parts: create server → define tools → run it.

```python
# MCP/server.py
from fastmcp import FastMCP
from utils.config import MCP_HOST, MCP_PORT, MCP_AUTH_TOKEN
from utils.logger import log


def create_mcp_server(auth_token: str = MCP_AUTH_TOKEN) -> FastMCP:
    auth_obj = None
    if auth_token:
        try:
            import importlib
            auth_mod = importlib.import_module("fastmcp.auth")
            bearer_cls = getattr(auth_mod, "BearerAuth", None)
            if bearer_cls:
                auth_obj = bearer_cls(token=auth_token)
        except Exception:
            auth_obj = None

    mcp = FastMCP("MonArch AI Tools", auth=auth_obj) if auth_obj else FastMCP("MonArch AI Tools")

    # 1️⃣ Hybrid RAG Search
    @mcp.tool
    def retrieve_documents(query: str, user_id: str = "") -> str:
        """Search ingested documents using hybrid RAG (FAISS semantic + BM25 keyword + RRF fusion)."""
        try:
            if not query or not query.strip():
                return "Error: query cannot be empty."
            from RAG.manager import rag_manager
            return rag_manager.retrieve(query.strip(), user_id=user_id.strip() or None)
        except Exception as e:
            return f"Error retrieving documents: {e}"

    # 2️⃣ Document Ingestion
    @mcp.tool
    def ingest_document(file_path: str, user_id: str = "") -> str:
        """Ingest a document file (PDF, DOCX, TXT, OCR) into the RAG vector store."""
        try:
            import os
            if not file_path or not file_path.strip():
                return "Error: file_path cannot be empty."
            resolved_path = os.path.abspath(os.path.normpath(file_path.strip()))
            if not os.path.isfile(resolved_path):
                return f"Error: file not found at '{file_path}'"
            from RAG.manager import rag_manager
            res = rag_manager.ingest(resolved_path, user_id=user_id.strip() or None)
            return f"Successfully ingested '{os.path.basename(resolved_path)}': {res.get('chunks_added', 0)} chunks indexed."
        except Exception as e:
            return f"Error ingesting document: {e}"

    # 3️⃣ Web Search
    @mcp.tool
    def web_search(query: str) -> str:
        """Search the web with DuckDuckGo and return top 5 results."""
        try:
            if not query or not query.strip():
                return "Error: search query cannot be empty."
            from duckduckgo_search import DDGS
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query.strip(), max_results=5):
                    results.append(f"• {r['title']}\n  {r['body']}\n  {r['href']}")
            return "\n\n".join(results) if results else "No results found."
        except Exception as e:
            return f"Error performing web search: {e}"

    # 4️⃣ Safe Calculator
    @mcp.tool
    def calculator(expression: str) -> str:
        """Safely evaluate a basic math expression. Example: '2 + 2 * 10'"""
        try:
            from MCP.server import _safe_eval_math
            return str(_safe_eval_math(expression))
        except Exception as e:
            return f"Error evaluating expression: {e}"

    return mcp


def run_mcp_server(host: str = MCP_HOST, port: int = MCP_PORT, auth_token: str = MCP_AUTH_TOKEN, **kwargs):
    mcp = create_mcp_server(auth_token=auth_token)
    log.info("Starting MonArch MCP server → http://%s:%d/mcp", host, port)
    mcp.run(transport="streamable-http", host=host, port=port, **kwargs)
```

Step 4 — Add a CLI Flag in main.py

```python
# main.py
import argparse
from utils.config import MCP_HOST, MCP_PORT, MCP_AUTH_TOKEN


def main():
    parser = argparse.ArgumentParser(description="MonArch AI — CLI Entrypoint")
    parser.add_argument("--serve-mcp", action="store_true", help="Run as MCP server")
    parser.add_argument("--mcp-host", default=MCP_HOST, help="MCP server host")
    parser.add_argument("--mcp-port", type=int, default=MCP_PORT, help="MCP server port")
    parser.add_argument("--mcp-auth-token", default=MCP_AUTH_TOKEN, help="Bearer auth token")
    args = parser.parse_args()

    if args.serve_mcp:
        from MCP.server import run_mcp_server
        run_mcp_server(host=args.mcp_host, port=args.mcp_port, auth_token=args.mcp_auth_token)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
```

Step 5 — Run the MCP Server

```bash
python main.py --serve-mcp
```

You'll see:

```text
2026-09-17 | INFO    | rag | Starting MonArch MCP server → http://127.0.0.1:8001/mcp
```

Your tools are now live at: `http://127.0.0.1:8001/mcp`

Step 6 — Connect to Claude Desktop
Open Claude Desktop's config file:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add your server:

```json
{
  "mcpServers": {
    "monarch-ai": {
      "url": "http://127.0.0.1:8001/mcp",
      "transport": "streamable-http"
    }
  }
}
```

Restart Claude Desktop. You'll see a 🔌 icon — your tools are available!

Step 7 — Connect to Cursor / VS Code
In Cursor settings (`~/.cursor/mcp.json`):

```json
{
  "servers": {
    "monarch-ai": {
      "url": "http://127.0.0.1:8001/mcp"
    }
  }
}
```

How It Actually Works (Under the Hood)

1. Claude gets a question: *"What do my ingested docs say about payment terms?"*
2. Claude sees tool list from your MCP server: `[retrieve_documents, ingest_document, web_search, calculator]`
3. Claude calls: `retrieve_documents(query="payment terms", user_id="user_1")`
4. Your server runs the function → returns context string
5. Claude uses the context to answer
The AI decides when and how to call your tools. You just define them.

🛠️ How to Write a Good Tool
Rule 1 — Clear docstring = good AI decisions
python

@mcp.tool
def get_invoice_status(invoice_id: str) -> str:
    """
    Get the payment status of an invoice by its ID.
    Returns: 'paid', 'pending', or 'overdue' with the due date.
    """
    ...
Rule 2 — Always return a string
python

@mcp.tool
def get_user_count() -> str:
    count = db.count_users()
    return f"There are {count} registered users."   # ✅
    # return count                                  # ❌ int won't work
Rule 3 — Handle errors gracefully
python

@mcp.tool
def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    try:
        import requests
        r = requests.get(url, timeout=10)
        return r.text[:2000]   # limit output
    except Exception as e:
        return f"Error fetching {url}: {e}"
Transport Options
Transport	Best For
streamable-http	Production, remote clients, Claude Desktop ✅
stdio	Local CLI tools, scripts
sse	Legacy SSE clients
Full Standalone Example (Zero Other Dependencies)
Test MCP completely on its own — no RAG, no LLM needed:

python

# server_standalone.py
from fastmcp import FastMCP
mcp = FastMCP("Demo Tools")
@mcp.tool
def greet(name: str) -> str:
    """Greet a person by name."""
    return f"Hello, {name}! 👋"
@mcp.tool
def add_numbers(a: float, b: float) -> str:
    """Add two numbers together."""
    return f"{a} + {b} = {a + b}"
@mcp.tool
def word_count(text: str) -> str:
    """Count the words in a piece of text."""
    count = len(text.split())
    return f"'{text[:30]}...' has {count} words."
if __name__ == "__main__":
    print("MCP server running at http://127.0.0.1:8001/mcp")
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8001)
```

```bash
pip install fastmcp
python server_standalone.py
# Point Claude Desktop at http://127.0.0.1:8001/mcp ✅
```

### Optional Upgrades

| Upgrade | How |
| :--- | :--- |
| **Add auth** | `mcp = FastMCP("Tools", auth=BearerAuth(token="secret"))` or pass `--mcp-auth-token` |
| **Split tool files** | Create `MCP/tools/rag_tools.py`, import into `server.py` |
| **Deploy to server** | Change host to `0.0.0.0`, put behind reverse proxy |
| **Add resources** | `@mcp.resource("docs://readme")` → exposes static content |
| **Add prompts** | `@mcp.prompt` → reusable prompt templates for LLMs |

### Quick Reference Cheat Sheet

```bash
# Install
pip install fastmcp duckduckgo-search

# Run
python main.py --serve-mcp

# Test it's alive
curl http://127.0.0.1:8001/mcp

# Claude Desktop config location (Windows)
%APPDATA%\Claude\claude_desktop_config.json
```

**TL;DR**: `@mcp.tool` on any function + `mcp.run(transport="streamable-http")` = that function is now callable by any AI client. That's it.