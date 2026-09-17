import os
from typing import Optional
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

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
        self.all_documents: list[Document] = []
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
        ext = os.path.splitext(file_path)[1].lower()
        docs: list[Document] = []

        # 1️⃣ Try Unstructured (best quality, needs API key or local install)
        if UNSTRUCTURED_API_KEY:
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
                    content = (
                        f"[OCR Text]\n{ocr_text}"
                        if ocr_text.strip()
                        else f"[Image: {os.path.basename(file_path)}]"
                    )
                    docs = [Document(page_content=content, metadata={"source": file_path})]
                except Exception:
                    docs = [
                        Document(
                            page_content=f"[Image: {os.path.basename(file_path)}]",
                            metadata={"source": file_path},
                        )
                    ]
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
        log.info(
            "Ingested %d chunks from '%s' (user_id=%s)",
            len(chunks),
            file_path,
            user_id,
        )
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
            user_filtered = [
                d
                for d in self.all_documents
                if d.metadata.get("user_id") in (user_id, None)
            ]
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
            matching_docs = [
                d for d in raw_docs if d.metadata.get("user_id") in (user_id, None)
            ]
        else:
            matching_docs = raw_docs

        # Remove the bootstrap placeholder
        matching_docs = [
            d for d in matching_docs if "RAG baseline" not in d.page_content
        ]

        # Smart fallback for broad/overview queries
        overview_keywords = {
            "paper",
            "document",
            "file",
            "pdf",
            "summarize",
            "about",
            "overview",
            "what",
        }
        is_broad = (
            any(kw in query.lower() for kw in overview_keywords)
            or len(query.split()) <= 4
        )
        if not matching_docs or is_broad:
            fallback = [
                d for d in valid_docs if "RAG baseline" not in d.page_content
            ][:5]
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
