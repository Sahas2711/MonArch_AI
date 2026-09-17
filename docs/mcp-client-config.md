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

| Tool | Description |
|:---|:---|
| `retrieve_documents` | Hybrid RAG search (FAISS + BM25 + RRF) across ingested documents |
| `ingest_document` | Ingest a PDF, DOCX, TXT, or image into the RAG vector store |
| `web_search` | Search the web via DuckDuckGo (top 5 results) |
| `calculator` | Evaluate basic math expressions |

---

## Custom Host / Port

Override the defaults via CLI flags or `.env`:

```bash
# CLI
python main.py --serve-mcp --mcp-host 0.0.0.0 --mcp-port 9000

# .env
MCP_HOST=0.0.0.0
MCP_PORT=9000
```

Update the client config URL accordingly (e.g., `http://your-server-ip:9000/mcp`).
