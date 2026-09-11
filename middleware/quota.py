"""
middleware/quota.py — SaaS Multi-Tenant Org & Quota Management (Vasooli / Wemboo)

SECURITY RULES ENFORCED:
1. org_id MUST be derived from user_id via org_members table, NEVER from request body/params (prevents IDOR).
2. Postgres uses ON CONFLICT DO NOTHING (not SQLite INSERT OR IGNORE).
3. check_quota is async and compatible with asyncpg pool and SQLite fallback.
4. Quotas are enforced against monthly usage events and plan definitions.
"""
import uuid
from typing import Any, Dict, Optional, Tuple
from fastapi import HTTPException, status
from SQL.db import get_pg_pool, get_sqlite_connection
from utils.logger import log

PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
    "free": {
        "analyses": 5,
        "documents": 10,
        "chat_messages": 100,
        "api_access": False,
        "price_inr": 0,
        "name": "Free Tier",
    },
    "pro": {
        "analyses": 50,
        "documents": 100,
        "chat_messages": 1000,
        "api_access": True,
        "price_inr": 999,
        "name": "Pro Plan",
    },
    "enterprise": {
        "analyses": -1,  # unlimited
        "documents": -1,
        "chat_messages": -1,
        "api_access": True,
        "price_inr": 4999,
        "name": "Enterprise Plan",
    },
}


async def get_user_org(user: Any) -> Tuple[str, str]:
    """
    Derive org_id and plan from the authenticated user's org_members row.
    NEVER accept org_id from a request parameter — that's an IDOR vulnerability.
    Returns (org_id, plan). Auto-provisions a free personal org if none found.
    """
    user_id = getattr(user, "user_id", str(user)) if not isinstance(user, str) else user
    email = getattr(user, "email", f"{user_id}@wemboo.internal") if not isinstance(user, str) else f"{user_id}@wemboo.internal"

    pool = await get_pg_pool()
    if pool is not None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT om.org_id, o.plan
                FROM org_members om
                JOIN organizations o ON o.id = om.org_id
                WHERE om.user_id = $1
                ORDER BY om.joined_at ASC
                LIMIT 1
                """,
                user_id,
            )
            if row:
                return str(row["org_id"]), str(row["plan"])
    else:
        # Dev / SQLite fallback
        conn = get_sqlite_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT om.org_id, o.plan
                FROM org_members om
                JOIN organizations o ON o.id = om.org_id
                WHERE om.user_id = ?
                ORDER BY om.joined_at ASC
                LIMIT 1
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            if row:
                return str(row["org_id"]), str(row["plan"])
        except Exception as exc:
            log.warning("SQLite org lookup error: %s", exc)
        finally:
            conn.close()

    # Auto-provision free personal workspace on first access
    return await _provision_personal_org(user_id, email)


async def _provision_personal_org(user_id: str, email: Optional[str] = None) -> Tuple[str, str]:
    """Auto-create a free personal org for a new user on first analysis."""
    clean_user_id = user_id.replace("-", "_")
    org_id = f"org_{clean_user_id[:8]}" if not user_id.startswith("org_") else str(uuid.uuid4())
    email_clean = email or f"{user_id}@wemboo.internal"
    workspace_name = f"{email_clean.split('@')[0]}'s Workspace"

    pool = await get_pg_pool()
    if pool is not None:
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO organizations (id, name, plan, monthly_quota, current_usage, billing_email)
                    VALUES ($1, $2, 'free', 5, 0, $3)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    org_id,
                    workspace_name,
                    email_clean,
                )
                await conn.execute(
                    """
                    INSERT INTO org_members (org_id, user_id, role)
                    VALUES ($1, $2, 'owner')
                    ON CONFLICT (user_id, org_id) DO NOTHING
                    """,
                    org_id,
                    user_id,
                )
        log.info("PostgreSQL: Auto-provisioned personal free org %s for user %s", org_id, user_id)
        return org_id, "free"

    # SQLite fallback
    conn = get_sqlite_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO organizations (id, name, plan, monthly_quota, current_usage, billing_email)
            VALUES (?, ?, 'free', 5, 0, ?)
            """,
            (org_id, workspace_name, email_clean),
        )
        cursor.execute(
            """
            INSERT OR IGNORE INTO org_members (user_id, org_id, role)
            VALUES (?, ?, 'owner')
            """,
            (user_id, org_id),
        )
        conn.commit()
        log.info("SQLite: Auto-provisioned personal free org %s for user %s", org_id, user_id)
        return org_id, "free"
    except Exception as exc:
        log.error("Error provisioning personal org in SQLite: %s", exc)
        return org_id, "free"
    finally:
        conn.close()


EVENT_TYPE_TO_LIMIT_KEY: Dict[str, str] = {
    "analysis": "analyses",
    "analyses": "analyses",
    "document": "documents",
    "documents": "documents",
    "chat": "chat_messages",
    "chat_messages": "chat_messages",
    "ingest": "documents",
}


async def verify_org_access(
    user: Any,
    org_id: Optional[str] = None,
    required_role: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    IDOR Security Guard:
    Verifies that the authenticated user is an active member of the specified org_id.
    If org_id is None, 'current', or 'me', resolves the caller's default org.
    Raises HTTP 403 Forbidden if user is not a verified member or lacks the required role.
    Returns (org_id, plan, role).
    """
    user_id = getattr(user, "user_id", str(user)) if not isinstance(user, str) else user
    target_org_id = None if (not org_id or org_id in ("current", "me", "default")) else org_id

    pool = await get_pg_pool()
    if pool is not None:
        async with pool.acquire() as conn:
            if target_org_id:
                row = await conn.fetchrow(
                    """
                    SELECT om.org_id, om.role, o.plan
                    FROM org_members om
                    JOIN organizations o ON o.id = om.org_id
                    WHERE om.user_id = $1 AND om.org_id = $2
                    LIMIT 1
                    """,
                    user_id,
                    target_org_id,
                )
            else:
                row = await conn.fetchrow(
                    """
                    SELECT om.org_id, om.role, o.plan
                    FROM org_members om
                    JOIN organizations o ON o.id = om.org_id
                    WHERE om.user_id = $1
                    ORDER BY om.joined_at ASC
                    LIMIT 1
                    """,
                    user_id,
                )
            if row:
                resolved_org_id = str(row["org_id"])
                user_role = str(row["role"])
                plan = str(row["plan"])
                if required_role and required_role == "owner" and user_role != "owner":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Action requires organization owner permissions.",
                    )
                if required_role and required_role in ("owner", "admin") and user_role not in ("owner", "admin"):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Action requires organization admin permissions.",
                    )
                return resolved_org_id, plan, user_role
    else:
        conn = get_sqlite_connection()
        try:
            cursor = conn.cursor()
            if target_org_id:
                cursor.execute(
                    """
                    SELECT om.org_id, om.role, o.plan
                    FROM org_members om
                    JOIN organizations o ON o.id = om.org_id
                    WHERE om.user_id = ? AND om.org_id = ?
                    LIMIT 1
                    """,
                    (user_id, target_org_id),
                )
            else:
                cursor.execute(
                    """
                    SELECT om.org_id, om.role, o.plan
                    FROM org_members om
                    JOIN organizations o ON o.id = om.org_id
                    WHERE om.user_id = ?
                    ORDER BY om.joined_at ASC
                    LIMIT 1
                    """,
                    (user_id,),
                )
            row = cursor.fetchone()
            if row:
                resolved_org_id = str(row["org_id"])
                user_role = str(row["role"])
                plan = str(row["plan"])
                if required_role and required_role == "owner" and user_role != "owner":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Action requires organization owner permissions.",
                    )
                if required_role and required_role in ("owner", "admin") and user_role not in ("owner", "admin"):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Action requires organization admin permissions.",
                    )
                return resolved_org_id, plan, user_role
        except HTTPException:
            raise
        except Exception as exc:
            log.warning("SQLite verify_org_access error: %s", exc)
        finally:
            conn.close()

    if target_org_id:
        log.warning("IDOR attempt blocked: user %s tried accessing org %s", user_id, target_org_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You are not a member of the specified organization.",
        )

    # If no org exists yet for this user, auto-provision
    email = getattr(user, "email", f"{user_id}@wemboo.internal") if not isinstance(user, str) else f"{user_id}@wemboo.internal"
    prov_org_id, prov_plan = await _provision_personal_org(user_id, email)
    return prov_org_id, prov_plan, "owner"


async def check_quota(user: Any, event_type: str = "analysis") -> str:
    """
    Enforces plan limits. Returns the verified org_id for use in subsequent DB writes.
    Raises HTTP 429 if quota is exceeded.
    org_id is ALWAYS derived from user identity — never from request input.
    """
    org_id, plan = await get_user_org(user)
    limit_key = EVENT_TYPE_TO_LIMIT_KEY.get(event_type, "analyses")
    tier_info = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    limit = tier_info.get(limit_key, 5)

    if limit == -1:  # Unlimited tier (enterprise)
        return org_id

    used = 0
    pool = await get_pg_pool()
    if pool is not None:
        async with pool.acquire() as conn:
            used = await conn.fetchval(
                """
                SELECT COUNT(*) FROM usage_events
                WHERE org_id = $1 AND event_type = $2
                  AND created_at >= date_trunc('month', now())
                """,
                org_id,
                event_type,
            ) or 0
    else:
        conn = get_sqlite_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM usage_events
                WHERE org_id = ? AND event_type = ?
                  AND strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now')
                """,
                (org_id, event_type),
            )
            row = cursor.fetchone()
            used = row[0] if row else 0
        except Exception as exc:
            log.warning("Error checking usage count in SQLite: %s", exc)
        finally:
            conn.close()

    if used >= limit:
        log.warning("Quota exceeded for org %s (plan %s, used %d/%d)", org_id, plan, used, limit)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "quota_exceeded",
                "plan": plan,
                "limit": limit,
                "used": used,
                "event_type": event_type,
                "upgrade_url": "/pricing",
                "message": f"Monthly limit reached ({used}/{limit} {limit_key}). Upgrade your plan to continue.",
            },
        )

    return org_id



async def log_usage_event(
    org_id: str,
    user_id: str,
    event_type: str = "analysis",
    tokens_used: int = 0,
) -> None:
    """Record an async usage event for metering and increment org counter."""
    event_id = str(uuid.uuid4())
    pool = await get_pg_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        """
                        INSERT INTO usage_events (id, org_id, user_id, event_type, tokens_used)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        event_id,
                        org_id,
                        user_id,
                        event_type,
                        tokens_used,
                    )
                    await conn.execute(
                        "UPDATE organizations SET current_usage = current_usage + 1 WHERE id = $1",
                        org_id,
                    )
        except Exception as exc:
            log.error("Failed to log usage event to Postgres: %s", exc)
    else:
        conn = get_sqlite_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO usage_events (id, org_id, user_id, event_type, tokens_used)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_id, org_id, user_id, event_type, tokens_used),
            )
            cursor.execute(
                "UPDATE organizations SET current_usage = current_usage + 1 WHERE id = ?",
                (org_id,),
            )
            conn.commit()
        except Exception as exc:
            log.error("Failed to log usage event to SQLite: %s", exc)
        finally:
            conn.close()


async def get_org_details(org_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve organization metadata, plan details, and active usage."""
    pool = await get_pg_pool()
    if pool is not None:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, plan, monthly_quota, current_usage, billing_email, created_at FROM organizations WHERE id = $1",
                org_id,
            )
            if row:
                res = dict(row)
                res["plan_info"] = PLAN_LIMITS.get(res["plan"], PLAN_LIMITS["free"])
                return res
    else:
        conn = get_sqlite_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, plan, monthly_quota, current_usage, billing_email, created_at FROM organizations WHERE id = ?",
                (org_id,),
            )
            row = cursor.fetchone()
            if row:
                res = {
                    "id": row["id"],
                    "name": row["name"],
                    "plan": row["plan"],
                    "monthly_quota": row["monthly_quota"],
                    "current_usage": row["current_usage"],
                    "billing_email": row["billing_email"],
                    "created_at": str(row["created_at"]),
                }
                res["plan_info"] = PLAN_LIMITS.get(res["plan"], PLAN_LIMITS["free"])
                return res
        except Exception as exc:
            log.warning("SQLite get_org_details error: %s", exc)
        finally:
            conn.close()
    return None


async def upgrade_org_plan(org_id: str, new_plan: str) -> bool:
    """Upgrade an organization's plan tier (called via Razorpay checkout / webhook)."""
    if new_plan not in PLAN_LIMITS:
        return False

    quota = PLAN_LIMITS[new_plan]["analyses"]
    pool = await get_pg_pool()
    if pool is not None:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE organizations SET plan = $1, monthly_quota = $2 WHERE id = $3",
                    new_plan,
                    quota,
                    org_id,
                )
            log.info("PostgreSQL: Upgraded org %s to %s (quota=%d)", org_id, new_plan, quota)
            return True
        except Exception as exc:
            log.error("Failed to upgrade org in Postgres: %s", exc)
            return False
    else:
        conn = get_sqlite_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE organizations SET plan = ?, monthly_quota = ? WHERE id = ?",
                (new_plan, quota, org_id),
            )
            conn.commit()
            log.info("SQLite: Upgraded org %s to %s (quota=%d)", org_id, new_plan, quota)
            return True
        except Exception as exc:
            log.error("Failed to upgrade org in SQLite: %s", exc)
            return False
        finally:
            conn.close()
