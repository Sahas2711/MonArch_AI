"""
Tamper-Evident Audit Event Logger.

Maintains an immutable chain of audit events where every event is cryptographically
hashed and linked to the previous event hash (SHA-256 hash-chain audit).
Supports persistent SQLite storage and chain verification from disk.
"""

import hashlib
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from vasooli.domain.errors import AuditIntegrityError
from vasooli.domain.models import AuditEvent


class AuditTrailManager:
    """
    Manages structured, tamper-evident audit event logging with optional SQLite persistence.
    """

    def __init__(self, org_id: str = "ORG-DEFAULT", db_path: Optional[str] = None):
        self.org_id = org_id
        self.db_path = db_path
        self._events: List[AuditEvent] = []
        self._last_hash: str = "0000000000000000000000000000000000000000000000000000000000000000"

        if self.db_path:
            self._init_db()
            self.load_events_from_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not self.db_path:
            raise ValueError("db_path not set for AuditTrailManager")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        if not self.db_path:
            return
        conn = self._get_conn()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_events (
                        event_id TEXT PRIMARY KEY,
                        org_id TEXT NOT NULL,
                        actor_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        resource_id TEXT NOT NULL,
                        resource_type TEXT NOT NULL DEFAULT 'analysis',
                        changes TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
        finally:
            conn.close()

    def load_events_from_db(self) -> List[AuditEvent]:
        """Loads and rebuilds in-memory audit event chain from database."""
        if not self.db_path:
            return self._events

        conn = self._get_conn()
        try:
            cur = conn.execute(
                "SELECT * FROM audit_events WHERE org_id = ? ORDER BY created_at ASC",
                (self.org_id,),
            )
            rows = cur.fetchall()
            self._events = []
            self._last_hash = "0000000000000000000000000000000000000000000000000000000000000000"

            for r in rows:
                ev = AuditEvent(
                    event_id=r["event_id"],
                    org_id=r["org_id"],
                    actor_id=r["actor_id"],
                    event_type=r["event_type"],
                    resource_id=r["resource_id"],
                    resource_type=r["resource_type"],
                    changes=json.loads(r["changes"]),
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
                self._events.append(ev)
                self._last_hash = ev.changes.get("event_hash", self._last_hash)
        finally:
            conn.close()

        return self._events

    def record_event(
        self,
        event_type: str,
        actor_id: str,
        resource_id: str,
        changes: Dict[str, Any],
        resource_type: str = "analysis",
    ) -> AuditEvent:
        """
        Records a new audit event and computes its cryptographic hash.
        Persists to SQLite if db_path is configured.
        """
        event_id = f"AUD-{len(self._events)+1:06d}"
        now = datetime.utcnow()

        # Compute payload hash
        payload_bytes = json.dumps(changes, sort_keys=True, default=str).encode("utf-8")
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()

        # Compute chain hash linking previous event
        block_content = f"{event_id}|{event_type}|{actor_id}|{resource_id}|{payload_hash}|{self._last_hash}|{now.isoformat()}"
        event_hash = hashlib.sha256(block_content.encode("utf-8")).hexdigest()

        event_changes = {
            **changes,
            "payload_hash": payload_hash,
            "prev_hash": self._last_hash,
            "event_hash": event_hash,
        }

        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            actor_id=actor_id,
            org_id=self.org_id,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=event_changes,
            created_at=now,
        )

        if self.db_path:
            conn = self._get_conn()
            try:
                with conn:
                    conn.execute(
                        """
                        INSERT INTO audit_events
                        (event_id, org_id, actor_id, event_type, resource_id, resource_type, changes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            event.event_id,
                            event.org_id,
                            event.actor_id,
                            event.event_type,
                            event.resource_id,
                            event.resource_type,
                            json.dumps(event.changes, default=str),
                            event.created_at.isoformat(),
                        ),
                    )
            finally:
                conn.close()

        self._events.append(event)
        self._last_hash = event_hash
        return event

    def verify_integrity(self) -> bool:
        """
        Verifies the cryptographic hash chain of all events.
        Raises AuditIntegrityError if any record has been modified.
        """
        expected_prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"

        for event in self._events:
            d = event.changes
            prev_hash = d.get("prev_hash")
            event_hash = d.get("event_hash")
            payload_hash = d.get("payload_hash")

            if prev_hash != expected_prev_hash:
                raise AuditIntegrityError(f"Audit chain broken at event {event.event_id}: previous hash mismatch.")

            clean_changes = {k: v for k, v in d.items() if k not in ["payload_hash", "prev_hash", "event_hash"]}
            recomputed_payload_hash = hashlib.sha256(
                json.dumps(clean_changes, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()

            if recomputed_payload_hash != payload_hash:
                raise AuditIntegrityError(f"Audit event {event.event_id} payload hash mismatch (tampering detected).")

            block_content = f"{event.event_id}|{event.event_type}|{event.actor_id}|{event.resource_id}|{recomputed_payload_hash}|{prev_hash}|{event.created_at.isoformat()}"
            recomputed_event_hash = hashlib.sha256(block_content.encode("utf-8")).hexdigest()

            if recomputed_event_hash != event_hash:
                raise AuditIntegrityError(f"Audit event {event.event_id} has been tampered with.")

            expected_prev_hash = event_hash

        return True

    def get_events(self) -> List[AuditEvent]:
        return list(self._events)
