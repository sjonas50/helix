"""Role-based access control.

Claude Code has no RBAC (single-user, USER_TYPE=ant for internal).
Helix adds per-resource, per-action permissions with role hierarchy.
"""


import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class Permission(BaseModel):
    """A single permission grant."""

    resource: str  # workflow | agent | memory | integration | approval | audit
    action: str  # create | read | update | delete | execute | approve
    conditions: dict[str, list[str]] = Field(default_factory=dict)


# Default role definitions
DEFAULT_ROLES: dict[str, list[Permission]] = {
    "admin": [
        Permission(resource="*", action="*"),
    ],
    "operator": [
        Permission(resource="workflow", action="create"),
        Permission(resource="workflow", action="read"),
        Permission(resource="workflow", action="update"),
        Permission(resource="agent", action="read"),
        Permission(resource="memory", action="read"),
        Permission(resource="memory", action="create"),
        Permission(resource="integration", action="read"),
        Permission(resource="integration", action="execute"),
        Permission(
            resource="approval",
            action="approve",
            conditions={"risk_level": ["LOW", "MEDIUM", "HIGH"]},
        ),
    ],
    "viewer": [
        Permission(resource="workflow", action="read"),
        Permission(resource="agent", action="read"),
        Permission(resource="memory", action="read"),
        Permission(resource="integration", action="read"),
    ],
    "auditor": [
        Permission(resource="audit", action="read"),
        Permission(resource="workflow", action="read"),
    ],
}


def has_permission(
    user_roles: list[str],
    resource: str,
    action: str,
    conditions: dict[str, str] | None = None,
) -> bool:
    """Check if a user with given roles has permission for a resource/action.

    Args:
        user_roles: List of role names assigned to the user.
        resource: The resource being accessed.
        action: The action being performed.
        conditions: Optional conditions to check (e.g., risk_level).
    """
    for role in user_roles:
        permissions = DEFAULT_ROLES.get(role, [])
        for perm in permissions:
            # Wildcard match
            if perm.resource == "*" and perm.action == "*":
                return True
            # Exact match
            if perm.resource == resource and perm.action in (action, "*"):
                # Check conditions if both sides have them
                if conditions and perm.conditions:
                    conditions_met = True
                    for key, value in conditions.items():
                        allowed = perm.conditions.get(key, [])
                        if allowed and value not in allowed:
                            conditions_met = False
                            break
                    if not conditions_met:
                        continue  # This permission doesn't match; try next
                return True
    return False


def get_user_permissions(roles: list[str]) -> list[Permission]:
    """Get all permissions for a set of roles."""
    permissions: list[Permission] = []
    for role in roles:
        permissions.extend(DEFAULT_ROLES.get(role, []))
    return permissions
