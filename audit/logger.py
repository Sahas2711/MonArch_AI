"""
Structured CloudWatch-Compatible Audit Logger.
Records every API request, route decision, token usage, latency, and guardrail action for compliance.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

_audit_logger = logging.getLogger("monarch.audit")
_audit_logger.setLevel(logging.INFO)

if not _audit_logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(message)s"))
    _audit_logger.addHandler(ch)


def log_audit_event(
    user_id: Optional[str],
    action: str,
    route: str,
    status: str = "success",
    latency_ms: float = 0.0,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Emit structured JSON log event for CloudWatch / AWS Audit Logs."""
    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user_id": user_id or "anonymous",
        "action": action,
        "route": route,
        "status": status,
        "latency_ms": round(latency_ms, 2),
        "metadata": metadata or {},
    }
    _audit_logger.info(json.dumps(event))


audit_logger = log_audit_event
