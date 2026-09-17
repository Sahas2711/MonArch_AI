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

python

# MCP/server.py
from fastmcp import FastMCP
from utils.logger import log
def run_mcp_server(host: str = "127.0.0.1", port: int = 8000):
    """Start FastMCP server exposing your tools over HTTP."""
    # 1️⃣ Create the MCP server with a name
    mcp = FastMCP("My AI Tools")
    # ---------------------------------------------------------------
    # 2️⃣ Define your tools — just use the @mcp.tool decorator
    # ---------------------------------------------------------------
    @mcp.tool
    def retriever_tool(query: str, user_id: str = "") -> str:
        """Retrieve relevant document context for a query from the RAG store."""
        from RAG.manager import rag_manager
        return rag_manager.retrieve(query, user_id=user_id or None)
    @mcp.tool
    def websearch_tool(query: str) -> str:
        """Search the web with DuckDuckGo and return results."""
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=5):
                results.append(f"• {r['title']}\n  {r['body']}\n  {r['href']}")
        return "\n\n".join(results) if results else "No results found."
    @mcp.tool
    def calculator_tool(expression: str) -> str:
        """Safely evaluate a math expression. Example: '2 + 2 * 10'"""
        try:
            allowed = set("0123456789+-*/.() ")
            if not all(c in allowed for c in expression):
                return "Error: only basic math operators allowed."
            result = eval(expression)
            return str(result)
        except Exception as e:
            return f"Error: {e}"
    # ---------------------------------------------------------------
    # 3️⃣ Run the server
    # ---------------------------------------------------------------
    log.info("Starting MCP server → http://%s:%d/mcp", host, port)
    mcp.run(transport="streamable-http", host=host, port=port)
Step 4 — Add a CLI Flag in main.py
python

# main.py
import argparse
def main():
    parser = argparse.ArgumentParser(description="My AI Project")
    parser.add_argument("--serve-mcp", action="store_true", help="Run as MCP server")
    args = parser.parse_args()
    if args.serve_mcp:
        from MCP.server import run_mcp_server
        run_mcp_server()
        return
    print("Hello! Add more commands here.")
if __name__ == "__main__":
    main()
Step 5 — Run the MCP Server
bash

python main.py --serve-mcp
You'll see:

2026-09-17 | INFO    | rag | Starting MCP server → http://127.0.0.1:8000/mcp
Your tools are now live at: http://127.0.0.1:8000/mcp

Step 6 — Connect to Claude Desktop
Open Claude Desktop's config file:

Windows: %APPDATA%\Claude\claude_desktop_config.json Mac: ~/Library/Application Support/Claude/claude_desktop_config.json

Add your server:

json

{
  "mcpServers": {
    "my-ai-tools": {
      "url": "http://127.0.0.1:8000/mcp",
      "transport": "streamable-http"
    }
  }
}
Restart Claude Desktop. You'll see a 🔌 icon — your tools are available!

Step 7 — Connect to Cursor / VS Code
In Cursor settings (~/.cursor/mcp.json):

json

{
  "servers": {
    "my-ai-tools": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
How It Actually Works (Under the Hood)

1. Claude gets a question: "What do my ingested docs say about contracts?"
2. Claude sees tool list from your MCP server: [retriever_tool, websearch_tool, ...]
3. Claude calls:  retriever_tool(query="contracts", user_id="user_1")
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
    print("MCP server running at http://127.0.0.1:8000/mcp")
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
bash

pip install fastmcp
python server_standalone.py
# Point Claude Desktop at http://127.0.0.1:8000/mcp ✅
Optional Upgrades
Upgrade	How
Add auth	mcp = FastMCP("Tools", auth=BearerAuth(token="secret"))
Split tool files	Create MCP/tools/rag_tools.py, import into server.py
Deploy to server	Change host to "0.0.0.0", put behind nginx
Add resources	@mcp.resource("docs://readme") → exposes static content
Add prompts	@mcp.prompt → reusable prompt templates for Claude
Quick Reference Cheat Sheet
bash

# Install
pip install fastmcp
# Run
python main.py --serve-mcp
# Test it's alive
curl http://127.0.0.1:8000/mcp
# Claude Desktop config location (Windows)
%APPDATA%\Claude\claude_desktop_config.json
TL;DR: @mcp.tool on any function + mcp.run() = that function is now callable by any AI. That's it.