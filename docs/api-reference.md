# Monarch — API Reference

## Base URL

```
http://localhost:8000
```

## Endpoints

### POST `/api/chat`

Execute a multi-agent investigation query.

**Request Body:**
```json
{
  "query": "Why did checkout start failing after deployment v2.4?",
  "chat_id": "optional-chat-id"
}
```

**Response:**
```json
{
  "response": "Root cause analysis with evidence chain...",
  "evidence_chain": [
    {
      "id": "E001",
      "source": "database.log",
      "line": 4821,
      "quote": "Connection pool exhausted...",
      "timestamp": "14:07:32"
    }
  ],
  "timeline": ["14:02:15", "14:04:30", "14:07:32", "14:08:01", "14:15:44"],
  "confidence": 0.91,
  "contradictions": {
    "hypothesis_a": "Database Connection Pool Exhaustion",
    "hypothesis_b": "Network Outage",
    "verdict": "Hypothesis A verified"
  }
}
```

---

### POST `/api/ingest`

Upload evidence files for RAG indexing.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `files` | File[] | Yes | Evidence files (logs, PDFs, images) |

**Supported Formats:**
- Text logs: `.log`, `.txt`
- Documents: `.pdf`, `.docx`
- Images: `.png`, `.jpg`, `.jpeg` (OCR via Tesseract)

**Response:**
```json
{
  "status": "success",
  "files_processed": 5,
  "evidence_ids": ["E001", "E002", "E003", "E004", "E005"]
}
```

---

### POST `/api/demo-incident`

Load the pre-built demo incident (INC-042) with sample evidence files.

**Request Body:** None

**Response:**
```json
{
  "status": "success",
  "incident_id": "INC-042",
  "files_loaded": [
    "deployment.log",
    "application.log",
    "database.log",
    "incident_report.md",
    "monitoring_dashboard.png"
  ]
}
```

---

### GET `/api/memories`

Retrieve active long-term memory facts.

**Response:**
```json
{
  "memories": [
    {
      "id": 1,
      "fact": "User prefers concise responses",
      "created_at": "2026-09-17T10:00:00Z"
    }
  ]
}
```

---

### POST `/api/memories`

Add a manual long-term memory fact.

**Request Body:**
```json
{
  "fact": "Production database uses connection pooling with max 50 connections"
}
```

**Response:**
```json
{
  "status": "success",
  "id": 2
}
```

---

### GET `/api/health`

System health check.

**Response:**
```json
{
  "status": "healthy",
  "groq_model": "openai/gpt-oss-20b",
  "langsmith_active": true,
  "langsmith_project": "Monarch",
  "version": "1.0.0"
}
```

---

### POST `/api/report`

Generate an executive incident report.

**Request Body:**
```json
{
  "incident_id": "INC-042",
  "investigation_result": { ... }
}
```

**Response:**
```json
{
  "report_markdown": "# Incident Report\n\n## Root Cause\n...",
  "report_html": "<h1>Incident Report</h1>..."
}
```

## Error Responses

| Status Code | Description |
|---|---|
| 400 | Bad Request — Invalid input |
| 404 | Not Found — Resource does not exist |
| 429 | Rate Limited — Too many requests |
| 500 | Internal Server Error |

## Rate Limiting

The API implements sliding-window rate limiting per IP address. Exceeding the limit returns HTTP 429 with a `Retry-After` header.
