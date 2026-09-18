"""
Role-Based Access Control (RBAC) Enforcer for Monarch Endpoints.
"""

from enum import Enum
from fastapi import HTTPException, status
from auth.cognito import UserContext


class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READ_ONLY = "read_only"


def require_role(user: UserContext, required_role: Role):
    """Verify that user possesses the required RBAC role level."""
    role_hierarchy = {Role.ADMIN: 3, Role.USER: 2, Role.READ_ONLY: 1}

    user_level = role_hierarchy.get(Role(user.role), 2)
    required_level = role_hierarchy.get(required_role, 2)

    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden: requires '{required_role.value}' permission role.",
        )
