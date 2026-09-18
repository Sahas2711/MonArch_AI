import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
from utils.logger import log


class DynamoDBManager:
    def __init__(self):
        self.table_name = os.getenv("DYNAMODB_TABLE_NAME", "MonarchSaaS")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self._resource = None

    def _get_resource(self):
        if self._resource is None and os.getenv("USE_DYNAMODB", "false").lower() == "true":
            try:
                import boto3
                self._resource = boto3.resource("dynamodb", region_name=self.region)
            except Exception as exc:
                log.warning("Could not initialize boto3 DynamoDB resource: %s", exc)
        return self._resource

    def get_table(self):
        res = self._get_resource()
        return res.Table(self.table_name) if res else None

    def get_org_member(self, user_id: str) -> Optional[Dict[str, Any]]:
        table = self.get_table()
        if not table:
            return None
        try:
            res = table.get_item(Key={"PK": f"USER#{user_id}", "SK": "METADATA"})
            return res.get("Item")
        except Exception as exc:
            log.warning("DynamoDB get_org_member error: %s", exc)
            return None

    def log_usage_event(self, org_id: str, user_id: str, event_type: str, tokens_used: int = 0):
        table = self.get_table()
        if not table:
            return
        try:
            now_iso = datetime.utcnow().isoformat()
            event_id = str(uuid.uuid4())
            table.put_item(
                Item={
                    "PK": f"ORG#{org_id}",
                    "SK": f"USAGE#{now_iso}#{event_id}",
                    "user_id": user_id,
                    "event_type": event_type,
                    "tokens_used": tokens_used,
                    "created_at": now_iso,
                }
            )
        except Exception as exc:
            log.error("DynamoDB log_usage_event error: %s", exc)


dynamo_manager = DynamoDBManager()
