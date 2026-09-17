from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
import shutil
import tempfile
import os

from RAG import rag_manager

app = FastAPI(title="MonArch AI", version="1.0.0")


class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None


class TextIngestRequest(BaseModel):
    content: str
    user_id: Optional[str] = None
    filename: Optional[str] = "direct_text_input.txt"


@app.get("/")
def root():
    return {"message": "MonArch AI API is running", "version": "1.0.0"}


@app.post("/rag/retrieve")
def retrieve_rag_context(payload: QueryRequest):
    """Retrieve relevant context using Hybrid RAG (FAISS + BM25 + RRF)."""
    try:
        context = rag_manager.retrieve(query=payload.query, user_id=payload.user_id)
        return {
            "query": payload.query,
            "user_id": payload.user_id,
            "context": context,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/rag/ingest-text")
def ingest_text(payload: TextIngestRequest):
    """Ingest raw text content into the RAG vector and keyword store."""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(payload.content)
            tmp_path = tmp.name

        try:
            result = rag_manager.ingest(tmp_path, user_id=payload.user_id)
            return {
                "status": "success",
                "chunks_added": result.get("chunks_added", 0),
                "filename": payload.filename,
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/rag/upload")
async def upload_document(
    file: UploadFile = File(...), user_id: Optional[str] = Form(None)
):
    """Upload and ingest a document (PDF, DOCX, TXT, Image, etc.) into RAG."""
    suffix = os.path.splitext(file.filename)[1]
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        try:
            result = rag_manager.ingest(tmp_path, user_id=user_id)
            return {
                "status": "success",
                "filename": file.filename,
                "chunks_added": result.get("chunks_added", 0),
                "user_id": user_id,
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
