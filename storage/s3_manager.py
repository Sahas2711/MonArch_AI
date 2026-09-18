"""
Amazon S3 Document Object Store Manager for Monarch.
Handles persistent upload of ingested raw documents and presigned download URL generation.
"""

import os
import uuid
from typing import Optional
from utils.logger import log


class S3DocumentManager:
    def __init__(self):
        self.bucket_name = os.getenv("S3_DOCUMENTS_BUCKET", "monarch-docs-storage")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self._client = None

    def _get_s3_client(self):
        if self._client is None:
            try:
                import boto3

                self._client = boto3.client("s3", region_name=self.region)
            except Exception as exc:
                log.warning("Could not initialize boto3 S3 client: %s", exc)
        return self._client

    def upload_document(
        self, file_path: str, file_name: str, user_id: Optional[str] = None
    ) -> dict:
        """
        Upload file to S3 under s3://bucket/{user_id}/{doc_id}/{filename}.
        Falls back gracefully if S3 client/credentials unavailable.
        """
        doc_id = str(uuid.uuid4())
        user_prefix = user_id or "global"
        s3_key = f"{user_prefix}/{doc_id}/{file_name}"

        client = self._get_s3_client()
        if client:
            try:
                client.upload_file(file_path, self.bucket_name, s3_key)
                s3_uri = f"s3://{self.bucket_name}/{s3_key}"
                log.info("Uploaded document %s to %s", file_name, s3_uri)
                return {"doc_id": doc_id, "s3_uri": s3_uri, "s3_key": s3_key}
            except Exception as exc:
                log.warning("S3 upload failed (%s). Continuing with local indexing.", exc)

        return {"doc_id": doc_id, "s3_uri": f"local://{file_path}", "s3_key": s3_key}

    def generate_presigned_url(self, s3_key: str, expiration_seconds: int = 3600) -> Optional[str]:
        """Generate presigned download URL for document UI."""
        client = self._get_s3_client()
        if not client:
            return None
        try:
            url = client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": s3_key},
                ExpiresIn=expiration_seconds,
            )
            return url
        except Exception as exc:
            log.error("Failed to generate presigned URL for %s: %s", s3_key, exc)
            return None


s3_manager = S3DocumentManager()
