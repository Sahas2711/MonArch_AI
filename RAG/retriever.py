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
            key = doc.page_content  # dedupe identical chunks
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
