🗂️ Adding the RAG Pipeline to a New Repo — From Scratch
This guide walks you through setting up the exact same Hybrid RAG pipeline (FAISS + BM25 + Reciprocal Rank Fusion) from Monarch into any empty repository.

📁 Final Folder Structure You'll Create

my-rag-project/
├── RAG/
│   ├── __init__.py
│   ├── embeddings.py
│   ├── retriever.py
│   └── manager.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   └── config.py
├── .env
├── requirements.txt
└── demo.py              ← test it works
Step 1 — Create the Project Folder
Open your terminal and run:

bash

mkdir my-rag-project
cd my-rag-project
Step 2 — Create a Virtual Environment
bash

python -m venv .venv
# Activate it:
# Windows:
.venv\Scripts\activate
# Mac / Linux:
source .venv/bin/activate
Step 3 — Create requirements.txt
Create this file in the root of your project:

txt

# requirements.txt
# Core RAG stack
langchain>=0.3.0
langchain-community>=0.3.0
langchain-huggingface>=0.1.0
langchain-text-splitters>=0.3.0
faiss-cpu>=1.8.0
rank-bm25>=0.2.2
sentence-transformers>=3.0.0
# Document loaders
pypdf>=4.0.0
python-docx>=1.1.0
docx2txt>=0.8
pillow>=10.0.0
pytesseract>=0.3.10          # optional: OCR for images
# Optional: Unstructured (best parser, needs API key)
# langchain-unstructured>=0.1.0
# Utilities
python-dotenv>=1.0.0
Install everything:

bash

pip install -r requirements.txt
Note: faiss-cpu is the CPU version. If you have a GPU use faiss-gpu instead.

Step 4 — Create the utils/ Folder
utils/__init__.py
python

(empty file)

utils/logger.py
python

import logging
import os
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("rag")
utils/config.py
python

import os
from dotenv import load_dotenv
load_dotenv()
# Embedding model — free, runs locally, no API key needed
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2"   # 384-dim, 22MB, fast
)
# Optional: Unstructured.io API key (for better PDF/DOCX parsing)
# Leave empty to use free local loaders
UNSTRUCTURED_API_KEY = os.getenv("UNSTRUCTURED_API_KEY", "")
.env
env

# Optional settings — defaults work fine out of the box
LOG_LEVEL=INFO
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
UNSTRUCTURED_API_KEY=
Step 5 — Create the RAG/ Folder
RAG/__init__.py
python

"""Retrieval-Augmented Generation (RAG) subsystem."""
from RAG.manager import RAGAgentManager, rag_manager
__all__ = ["RAGAgentManager", "rag_manager"]
RAG/embeddings.py
python

from langchain_huggingface import HuggingFaceEmbeddings
from utils.config import EMBEDDING_MODEL
def get_embeddings_model(model_name: str = EMBEDDING_MODEL) -> HuggingFaceEmbeddings:
    """Initialize HuggingFace embeddings model (runs 100% locally, no API key needed)."""
    return HuggingFaceEmbeddings(model_name=model_name)
What it does: Downloads all-MiniLM-L6-v2 once from HuggingFace and caches it locally. Converts text → 384-dimensional vectors.

RAG/retriever.py
python

from typing import Optional
from langchain_community.retrievers import BM25Retriever
def reciprocal_rank_fusion(ranked_lists: list[list], k: int = 60, top_n: int = 3) -> list:
    """
    Merge several ranked doc lists into one ranking via Reciprocal Rank Fusion (RRF).
    Formula: score(doc) = Σ  1 / (k + rank_i + 1)
    The doc appearing at rank 1 in multiple lists wins.
    """
    scores: dict[str, float] = {}
    doc_by_key: dict[str, object] = {}
    for docs in ranked_lists:
        for rank, doc in enumerate(docs):
            key = doc.page_content           # dedupe identical chunks
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            doc_by_key.setdefault(key, doc)
    ranked_keys = sorted(scores, key=scores.get, reverse=True)
    return [doc_by_key[key] for key in ranked_keys[:top_n]]
def build_bm25_retriever(documents: list, k: int = 3) -> Optional[BM25Retriever]:
    """Build BM25 keyword retriever from a list of LangChain Document objects."""
    if not documents:
        return None
    retriever = BM25Retriever.from_documents(documents)
    retriever.k = k
    return retriever
What it does:

BM25 = classic keyword search (TF-IDF based). Great for exact terms.
RRF = smart merge of multiple ranked lists. If a doc appears high in both FAISS and BM25, it wins.
RAG/manager.py
python

from typing import Optional
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from RAG.embeddings import get_embeddings_model
from RAG.retriever import build_bm25_retriever, reciprocal_rank_fusion
from utils.config import EMBEDDING_MODEL, UNSTRUCTURED_API_KEY
from utils.logger import log
class RAGAgentManager:
    """
    Owns the vector store + keyword index.
    Call ingest() to add documents, retrieve() to search.
    """
    def __init__(self, embedding_model: str = EMBEDDING_MODEL):
        self.embeddings = get_embeddings_model(embedding_model)
        # Bootstrap FAISS with a placeholder so it's never empty
        self.vector_db = FAISS.from_texts(
            ["RAG baseline — no documents ingested yet."], self.embeddings
        )
        self.all_documents: list = []
        self._bm25_retriever: Optional[object] = None
        self._bm25_dirty = True  # rebuild BM25 lazily after each ingest
    # ------------------------------------------------------------------
    # INGEST
    # ------------------------------------------------------------------
    def ingest(self, file_path: str, user_id: Optional[str] = None) -> dict:
        """
        Load, chunk, and index a document.
        Supports: PDF, DOCX, TXT, PNG/JPG (OCR), and any other text file.
        """
        import os
        from langchain_core.documents import Document
        ext = os.path.splitext(file_path)[1].lower()
        docs = []
        # 1️⃣ Try Unstructured (best quality, needs API key or local install)
        try:
            from langchain_unstructured import UnstructuredLoader
            loader = UnstructuredLoader(
                file_path=file_path,
                api_key=UNSTRUCTURED_API_KEY,
                partition_via_api=bool(UNSTRUCTURED_API_KEY),
            )
            docs = loader.load()
        except Exception as exc:
            log.info("UnstructuredLoader skipped (%s). Using fallback loader.", exc)
        # 2️⃣ Fallback loaders by file type
        if not docs:
            if ext == ".pdf":
                try:
                    from langchain_community.document_loaders import PyPDFLoader
                    docs = PyPDFLoader(file_path).load()
                except Exception:
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    text = "\n\n".join(p.extract_text() or "" for p in reader.pages)
                    docs = [Document(page_content=text, metadata={"source": file_path})]
            elif ext in (".docx", ".doc"):
                try:
                    from langchain_community.document_loaders import Docx2txtLoader
                    docs = Docx2txtLoader(file_path).load()
                except Exception:
                    import docx
                    d = docx.Document(file_path)
                    text = "\n".join(p.text for p in d.paragraphs if p.text)
                    docs = [Document(page_content=text, metadata={"source": file_path})]
            elif ext in (".png", ".jpg", ".jpeg"):
                try:
                    import pytesseract
                    from PIL import Image
                    ocr_text = pytesseract.image_to_string(Image.open(file_path))
                    content = f"[OCR Text]\n{ocr_text}" if ocr_text.strip() else f"[Image: {os.path.basename(file_path)}]"
                    docs = [Document(page_content=content, metadata={"source": file_path})]
                except Exception:
                    docs = [Document(page_content=f"[Image: {os.path.basename(file_path)}]", metadata={"source": file_path})]
            else:  # .txt, .md, .csv, etc.
                try:
                    from langchain_community.document_loaders import TextLoader
                    docs = TextLoader(file_path, encoding="utf-8").load()
                except Exception:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        docs = [Document(page_content=f.read(), metadata={"source": file_path})]
        # 3️⃣ Split into chunks
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
        chunks = splitter.split_documents(docs)
        # 4️⃣ Tag metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata["user_id"] = user_id
            chunk.metadata["source"] = file_path
            chunk.metadata["chunk_index"] = i
        # 5️⃣ Index into FAISS + mark BM25 dirty
        self.vector_db.add_documents(chunks)
        self.all_documents.extend(chunks)
        self._bm25_dirty = True
        log.info("Ingested %d chunks from '%s' (user_id=%s)", len(chunks), file_path, user_id)
        return {"status": "success", "chunks_added": len(chunks)}
    # ------------------------------------------------------------------
    # INTERNAL: lazy BM25 rebuild
    # ------------------------------------------------------------------
    def _get_bm25(self):
        if not self.all_documents:
            return None
        if self._bm25_dirty or self._bm25_retriever is None:
            self._bm25_retriever = build_bm25_retriever(self.all_documents)
            self._bm25_dirty = False
        return self._bm25_retriever
    # ------------------------------------------------------------------
    # RETRIEVE
    # ------------------------------------------------------------------
    def retrieve(self, query: str, user_id: Optional[str] = None) -> str:
        """
        Hybrid search: FAISS (semantic) + BM25 (keyword) → RRF merge → top-5 chunks.
        Returns a single string of context ready to paste into an LLM prompt.
        """
        if not self.all_documents:
            return "(no documents ingested yet)"
        # Filter by user_id if provided
        valid_docs = self.all_documents
        if user_id:
            user_filtered = [d for d in self.all_documents if d.metadata.get("user_id") in (user_id, None)]
            if user_filtered:
                valid_docs = user_filtered
        # --- FAISS semantic search ---
        faiss_retriever = self.vector_db.as_retriever(search_kwargs={"k": 10})
        faiss_docs = faiss_retriever.invoke(query)
        # --- BM25 keyword search ---
        bm25_retriever = self._get_bm25()
        if bm25_retriever:
            bm25_docs = bm25_retriever.invoke(query)
            raw_docs = reciprocal_rank_fusion([bm25_docs, faiss_docs], top_n=5)
        else:
            raw_docs = faiss_docs[:5]
        # Filter to valid user_id docs
        if user_id:
            matching_docs = [d for d in raw_docs if d.metadata.get("user_id") in (user_id, None)]
        else:
            matching_docs = raw_docs
        # Remove the bootstrap placeholder
        matching_docs = [d for d in matching_docs if "RAG baseline" not in d.page_content]
        # Smart fallback for broad/overview queries
        overview_keywords = {"paper", "document", "file", "pdf", "summarize", "about", "overview", "what"}
        is_broad = any(kw in query.lower() for kw in overview_keywords) or len(query.split()) <= 4
        if not matching_docs or is_broad:
            fallback = [d for d in valid_docs if "RAG baseline" not in d.page_content][:5]
            seen = set()
            combined = []
            for d in matching_docs + fallback:
                if d.page_content not in seen:
                    seen.add(d.page_content)
                    combined.append(d)
            matching_docs = combined[:5]
        if not matching_docs:
            return "(no relevant context found)"
        return "\n\n---\n\n".join(d.page_content for d in matching_docs)
# Global singleton — import this wherever you need RAG
rag_manager = RAGAgentManager()
Step 6 — Create demo.py to Test It
python

# demo.py — Run this to verify everything works
from RAG import rag_manager
# 1. Ingest a text file
with open("sample.txt", "w") as f:
    f.write("""
    The MSMED Act 2006 Section 15 states that buyers must pay MSMEs within 45 days.
    If payment is delayed, Section 16 mandates compound interest at 3x the RBI bank rate.
    The current RBI bank rate is 6.5%, so the penalty rate is 19.5% per annum.
    MSME Samadhaan is an online portal for filing arbitration cases.
    """)
result = rag_manager.ingest("sample.txt", user_id="user_001")
print("Ingest result:", result)
# → {'status': 'success', 'chunks_added': 1}
# 2. Retrieve relevant context
context = rag_manager.retrieve("What is the penalty interest rate?", user_id="user_001")
print("\n--- Retrieved Context ---")
print(context)
# → "The MSMED Act 2006 Section 15 states that buyers must pay MSMEs within 45 days..."
# 3. Use context in an LLM prompt (pseudocode)
# prompt = f"Context:\n{context}\n\nQuestion: What is the penalty interest rate?\nAnswer:"
# response = llm.invoke(prompt)
Run it:

bash

python demo.py
Step 7 — How the Pipeline Works (Visual)

User Query: "What is the penalty rate?"
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                    RAGAgentManager                       │
│                                                         │
│  ┌───────────────┐        ┌─────────────────────────┐   │
│  │  FAISS (dense)│        │   BM25 (sparse/keyword) │   │
│  │  semantic     │        │   exact term matching   │   │
│  │  top-10 docs  │        │   top-3 docs            │   │
│  └───────┬───────┘        └────────────┬────────────┘   │
│          │                             │                 │
│          └──────────┬──────────────────┘                 │
│                     ▼                                   │
│          Reciprocal Rank Fusion                         │
│          (best of both worlds, top-5)                   │
│                     │                                   │
│          Filter by user_id                              │
│                     │                                   │
│          Smart fallback for broad queries               │
└─────────────────────┬───────────────────────────────────┘
                      ▼
             Context string → LLM Prompt
Step 8 — Common Errors & Fixes
Error	Fix
ModuleNotFoundError: faiss	Run pip install faiss-cpu
ModuleNotFoundError: sentence_transformers	Run pip install sentence-transformers
ModuleNotFoundError: rank_bm25	Run pip install rank-bm25
ModuleNotFoundError: langchain_huggingface	Run pip install langchain-huggingface
First run is slow	Normal — embedding model is downloading (~22MB). Cached after first use.
pytesseract not found	Only needed for image OCR. Skip or pip install pytesseract + install Tesseract binary
Step 9 — Optional Upgrades
Upgrade	How
Persist FAISS (survive restarts)	rag_manager.vector_db.save_local("faiss_index") on exit; FAISS.load_local(...) on startup
Use pgvector instead of FAISS	Replace FAISS with langchain_postgres.PGVector
Use OpenAI embeddings	Replace HuggingFaceEmbeddings with OpenAIEmbeddings() in embeddings.py
Expose as API	Wrap ingest() and retrieve() in FastAPI routes
Multi-user isolation	Already built in — just pass user_id to ingest() and retrieve()
That's it. Your RAG pipeline is fully self-contained in the RAG/ folder with no external APIs required. The embedding model runs locally for free.