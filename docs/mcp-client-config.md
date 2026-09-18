# MCP Client Configuration Guide

Connect Claude Desktop, Cursor, or any MCP-compatible client to MonArch AI's MCP server.

---

## Prerequisites

Start the MCP server first:

```bash
python main.py --serve-mcp
```

Server will be live at: **http://127.0.0.1:8001/mcp**

---

## Claude Desktop

**Config file location:**
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Add this to the config file:**

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

Restart Claude Desktop. You'll see a 🔌 icon — MonArch tools are now available.

---

## Cursor / VS Code

**Config file**: `~/.cursor/mcp.json`

```json
{
  "servers": {
    "monarch-ai": {
      "url": "http://127.0.0.1:8001/mcp"
    }
  }
}
```

---

## Available Tools

Once connected, the AI client can call these tools:

| Tool | Parameters | Description | Input Validation / Limits |
|:---|:---|:---|:---|
| `retrieve_documents` (or `query_rag`) | `query: str`, `user_id: str = ""` | Hybrid RAG search (FAISS semantic + BM25 keyword + RRF fusion) | Non-empty query, max 4000 characters |
| `ingest_document` | `file_path: str`, `user_id: str = ""` | Ingest a document (PDF, DOCX, TXT, OCR images) into RAG | Path traversal sanitized, file existence check, extension whitelist, max 50MB |
| `web_search` | `query: str` | Search the web via DuckDuckGo (top 5 results) | Non-empty query, max 500 characters |
| `calculator` | `expression: str` | Safely evaluate basic math expressions | Safe AST evaluation (+, -, *, /, //, %, **), max 200 characters |

---

## Authentication (Optional)

To secure the MCP server with a Bearer token:

1. Set `MCP_AUTH_TOKEN` in `.env` or pass `--mcp-auth-token`:
```bash
python main.py --serve-mcp --mcp-auth-token "your-secret-token"
```

2. Add authentication headers in client configuration if required:
```json
{
  "mcpServers": {
    "monarch-ai": {
      "url": "http://127.0.0.1:8001/mcp",
      "transport": "streamable-http",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      }
    }
  }
}
```

---

## Custom Host / Port

Override the defaults via CLI flags or `.env`:

```bash
# CLI
python main.py --serve-mcp --mcp-host 0.0.0.0 --mcp-port 9000 --mcp-auth-token "secret"

# .env
MCP_HOST=0.0.0.0
MCP_PORT=9000
MCP_AUTH_TOKEN=secret
```

Update the client config URL accordingly (e.g., `http://your-server-ip:9000/mcp`).
