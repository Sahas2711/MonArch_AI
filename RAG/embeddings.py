from langchain_huggingface import HuggingFaceEmbeddings
from utils.config import EMBEDDING_MODEL


def get_embeddings_model(model_name: str = EMBEDDING_MODEL) -> HuggingFaceEmbeddings:
    """Initialize HuggingFace embeddings model (runs 100% locally, no API key needed)."""
    return HuggingFaceEmbeddings(model_name=model_name)
