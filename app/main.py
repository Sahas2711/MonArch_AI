from typing import Optional
from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import shutil
import tempfile
import os
import logging
import time
from collections import defaultdict

from RAG import rag_manager

logger = logging.getLogger("monarch.api")

API_VERSION = "1.0.0"
MAX_UPLOAD_SIZE_MB = 50
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "30"))
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".png", ".jpg", ".jpeg"}


class RateLimitMiddleware:
    def __init__(self, app, window: int = 60, max_requests: int = 30):
        self.app = app
        self.window = window
        self.max_requests = max_requests
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        client = scope.get("client")
        if client:
            ip = client[0]
            now = time.time()
            self.requests[ip] = [t for t in self.requests[ip] if now - t < self.window]
            if len(self.requests[ip]) >= self.max_requests:
                from starlette.responses import JSONResponse
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                )
                return await response(scope, receive, send)
            self.requests[ip].append(now)

        return await self.app(scope, receive, send)

app = FastAPI(title="MonArch AI", version=API_VERSION)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(RateLimitMiddleware, window=RATE_LIMIT_WINDOW, max_requests=RATE_LIMIT_MAX_REQUESTS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    user_id: Optional[str] = Field(None, max_length=200)


class TextIngestRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=500000)
    user_id: Optional[str] = Field(None, max_length=200)
    filename: Optional[str] = Field("direct_text_input.txt", max_length=255)


@app.get("/")
def root():
    return {"message": "MonArch AI API is running", "version": API_VERSION}


@app.post("/rag/retrieve")
async def retrieve_rag_context(payload: QueryRequest):
    """Retrieve relevant context using Hybrid RAG (FAISS + BM25 + RRF)."""
    try:
        context = rag_manager.retrieve(query=payload.query, user_id=payload.user_id)
        return {
            "query": payload.query,
            "user_id": payload.user_id,
            "context": context,
        }
    except Exception as exc:
        logger.error("RAG retrieve failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error during retrieval.")


@app.post("/rag/ingest-text")
async def ingest_text(payload: TextIngestRequest):
    """Ingest raw text content into the RAG vector and keyword store."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(payload.content)
            tmp_path = tmp.name

        result = rag_manager.ingest(tmp_path, user_id=payload.user_id)
        return {
            "status": "success",
            "chunks_added": result.get("chunks_added", 0),
            "filename": payload.filename,
        }
    except Exception as exc:
        logger.error("Text ingest failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error during text ingestion.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@app.post("/rag/upload")
async def upload_document(
    file: UploadFile = File(...), user_id: Optional[str] = Form(None)
):
    """Upload and ingest a document (PDF, DOCX, TXT, Image, etc.) into RAG."""
    # Validate file extension
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{suffix}' not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Validate file size
    content = await file.read()
    max_size = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB}MB.",
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        result = rag_manager.ingest(tmp_path, user_id=user_id)
        return {
            "status": "success",
            "filename": file.filename,
            "chunks_added": result.get("chunks_added", 0),
            "user_id": user_id,
        }
    except Exception as exc:
        logger.error("File upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Internal server error during file upload.")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
