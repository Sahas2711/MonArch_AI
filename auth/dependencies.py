"""
FastAPI Depends() Helper for Authenticated User Injection.
"""

from typing import Optional
from fastapi import Header
from auth.cognito import UserContext, verify_jwt_token


async def get_current_user(authorization: Optional[str] = Header(None)) -> UserContext:
    """FastAPI dependency injecting verified UserContext into API routes."""
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    return verify_jwt_token(token)
