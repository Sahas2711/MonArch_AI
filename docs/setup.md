# Monarch — Setup Guide

## Prerequisites

- Python 3.11+
- Groq API Key (free tier available)
- Git

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AWSWEMAKEDEV
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:

```env
GROQ_API_KEY=gsk_your_key_here
```

### 5. Start the Server

```bash
python main.py
```

Open http://localhost:8001 in your browser.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM access |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Groq model to use (auto-fallback if deprecated) |
| `EMBEDDING_MODEL` | No | `sentence-transformers/all-MiniLM-L6-v2` | Sentence-transformers model |
| `UNSTRUCTURED_API_KEY` | No | — | For advanced document parsing |
| `LANGCHAIN_API_KEY` | No | — | Enables LangSmith tracing |
| `LANGSMITH_API_KEY` | No | — | Alias for LANGCHAIN_API_KEY |
| `LANGCHAIN_PROJECT` | No | `Monarch` | LangSmith project name |
| `LANGSMITH_PROJECT` | No | — | Alias for LANGCHAIN_PROJECT |

---

## Docker Setup (Planned)

Docker support is planned but not yet implemented. See [Dockerfile](../Dockerfile) when available.

---

## Verifying Installation

### Health Check

```bash
curl http://localhost:8001/
```

Expected response:
```json
{
  "message": "MonArch AI API is running",
  "version": "1.0.0"
}
```

### Upload a Document

```bash
curl -X POST http://localhost:8001/rag/upload -F "file=@your_document.pdf"
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'langchain'"

```bash
pip install -r requirements.txt
```

### "GROQ_API_KEY not found"

Ensure `.env` exists and contains your key:
```bash
cp .env.example .env
# Edit .env with your actual key
```

### "Connection refused at localhost:8001"

Backend is not running. Start it:
```bash
python main.py
```

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8001 | xargs kill -9
```

---

## IDE Setup

### VS Code

Recommended extensions:
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- Docker (ms-azuretools.vscode-docker)

### Recommended Settings

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe",
  "python.terminal.activateEnvironment": true
}
```
