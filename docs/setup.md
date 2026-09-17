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
python api.py
```

Open http://localhost:8000 in your browser.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM access |
| `GROQ_MODEL` | No | `openai/gpt-oss-20b` | Groq model to use (auto-fallback if deprecated) |
| `EMBEDDING_MODEL` | No | `sentence-transformers/all-MiniLM-L6-v2` | Sentence-transformers model |
| `UNSTRUCTURED_API_KEY` | No | — | For advanced document parsing |
| `LANGCHAIN_API_KEY` | No | — | Enables LangSmith tracing |
| `LANGSMITH_API_KEY` | No | — | Alias for LANGCHAIN_API_KEY |
| `LANGCHAIN_PROJECT` | No | `Monarch` | LangSmith project name |
| `LANGSMITH_PROJECT` | No | — | Alias for LANGCHAIN_PROJECT |

---

## Docker Setup

### Build and Run

```bash
docker-compose up --build
```

The API will be available at http://localhost:8000.

### Docker Compose Services

| Service | Port | Description |
|---|---|---|
| `monarch-api` | 8000 | FastAPI backend |

---

## Verifying Installation

### Health Check

```bash
curl http://localhost:8000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "groq_model": "openai/gpt-oss-20b",
  "langsmith_active": false
}
```

### Load Demo Incident

```bash
curl -X POST http://localhost:8000/api/demo-incident
```

### Run Evaluation Harness

```bash
python -m harness.eval_suite
```

Outputs results to `evaluation_report.json`.

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

### "Connection refused at localhost:8000"

Backend is not running. Start it:
```bash
python api.py
```

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
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
