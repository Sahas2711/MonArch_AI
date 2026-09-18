"""
Amazon OpenSearch Serverless Vector Collection Provisioning & Helper Script.
Configures vector collection with k-NN vector field mappings (384 dimensions for all-MiniLM-L6-v2).
"""

import os
from typing import Optional
from utils.logger import log


def create_opensearch_vector_client(endpoint: Optional[str] = None):
    """
    Instantiate OpenSearch client using IAM authentication via boto3 if available,
    falling back to basic auth / host connection.
    """
    endpoint = endpoint or os.getenv("OPENSEARCH_ENDPOINT")
    if not endpoint:
        log.info("OPENSEARCH_ENDPOINT not configured. Using local FAISS vector store.")
        return None

    try:
        from opensearchpy import OpenSearch, RequestsHttpConnection
        from requests_aws4auth import AWS4Auth
        import boto3

        region = os.getenv("AWS_REGION", "us-east-1")
        service = "aoss"  # OpenSearch Serverless
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            service,
            session_token=credentials.token,
        )

        client = OpenSearch(
            hosts=[{"host": endpoint.replace("https://", ""), "port": 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
        )
        return client
    except Exception as exc:
        log.warning("Failed to create OpenSearch client (%s).", exc)
        return None


def get_index_mapping(vector_dim: int = 384) -> dict:
    """Return OpenSearch index template with k-NN vector indexing and metadata filters."""
    return {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 100}},
        "mappings": {
            "properties": {
                "vector_field": {
                    "type": "knn_vector",
                    "dimension": vector_dim,
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",
                        "engine": "nmslib",
                    },
                },
                "text": {"type": "text"},
                "user_id": {"type": "keyword"},
                "source": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
            }
        },
    }
