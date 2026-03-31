"""Tests for RBAC and token management."""

import uuid
from datetime import datetime, timedelta

from helix.auth.rbac import DEFAULT_ROLES, has_permission
from helix.auth.tokens import (
    create_token_claims,
    is_token_expired,
    validate_token_claims,
)


class TestRBAC:
    def test_admin_has_all_permissions(self) -> None:
        assert has_permission(["admin"], "workflow", "create")
        assert has_permission(["admin"], "memory", "delete")
        assert has_permission(["admin"], "anything", "anything")

    def test_operator_can_create_workflows(self) -> None:
        assert has_permission(["operator"], "workflow", "create")
        assert has_permission(["operator"], "workflow", "read")

    def test_operator_cannot_delete_workflows(self) -> None:
        assert not has_permission(["operator"], "workflow", "delete")

    def test_viewer_read_only(self) -> None:
        assert has_permission(["viewer"], "workflow", "read")
        assert has_permission(["viewer"], "memory", "read")
        assert not has_permission(["viewer"], "workflow", "create")
        assert not has_permission(["viewer"], "memory", "create")

    def test_auditor_limited_access(self) -> None:
        assert has_permission(["auditor"], "audit", "read")
        assert has_permission(["auditor"], "workflow", "read")
        assert not has_permission(["auditor"], "memory", "read")

    def test_multiple_roles_union(self) -> None:
        # viewer + auditor should combine permissions
        assert has_permission(["viewer", "auditor"], "memory", "read")  # from viewer
        assert has_permission(["viewer", "auditor"], "audit", "read")  # from auditor

    def test_unknown_role_no_permissions(self) -> None:
        assert not has_permission(["nonexistent"], "workflow", "read")

    def test_default_roles_defined(self) -> None:
        assert "admin" in DEFAULT_ROLES
        assert "operator" in DEFAULT_ROLES
        assert "viewer" in DEFAULT_ROLES
        assert "auditor" in DEFAULT_ROLES


class TestTokens:
    def test_user_token_24h_ttl(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["operator"],
            token_type="user",
        )
        delta = claims.exp - claims.iat
        assert 1439 <= delta.total_seconds() / 60 <= 1441  # ~24 hours

    def test_agent_token_15min_ttl(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["operator"],
            token_type="agent",
        )
        delta = claims.exp - claims.iat
        assert 14 <= delta.total_seconds() / 60 <= 16  # ~15 minutes

    def test_custom_ttl(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["admin"],
            ttl_minutes=5,
        )
        delta = claims.exp - claims.iat
        assert 4 <= delta.total_seconds() / 60 <= 6

    def test_token_not_expired(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["admin"],
        )
        assert not is_token_expired(claims)

    def test_token_expired(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["admin"],
            ttl_minutes=0,
        )
        # Force expiry
        claims.exp = datetime.now() - timedelta(minutes=1)
        assert is_token_expired(claims)

    def test_validate_valid_token(self) -> None:
        org_id = uuid.uuid4()
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=org_id,
            roles=["admin"],
        )
        valid, msg = validate_token_claims(claims, required_org_id=org_id)
        assert valid
        assert msg == ""

    def test_validate_expired_token(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["admin"],
        )
        claims.exp = datetime.now() - timedelta(hours=1)
        valid, msg = validate_token_claims(claims)
        assert not valid
        assert "expired" in msg.lower()

    def test_validate_wrong_org(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["admin"],
        )
        valid, msg = validate_token_claims(claims, required_org_id=uuid.uuid4())
        assert not valid
        assert "org" in msg.lower()
