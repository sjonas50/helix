"""Tests for auth: JWT signing/verification, RBAC, token lifecycle."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from helix.auth.rbac import DEFAULT_ROLES, has_permission
from helix.auth.tokens import (
    create_token_claims,
    decode_token,
    encode_token,
    validate_token_claims,
)
from helix.auth.workos import handle_scim_event, handle_sso_callback


class TestJWTRoundtrip:
    """Test real JWT encode/decode with python-jose."""

    def test_encode_decode_roundtrip(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["admin"],
        )
        token = encode_token(claims)
        assert isinstance(token, str)
        assert len(token) > 50  # JWT is a substantial string

        decoded = decode_token(token)
        assert decoded.sub == claims.sub
        assert decoded.org_id == claims.org_id
        assert decoded.roles == claims.roles
        assert decoded.token_type == claims.token_type

    def test_decode_invalid_token_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token("not.a.valid.jwt")

    def test_decode_tampered_token_raises(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["admin"],
        )
        token = encode_token(claims)
        # Tamper with the payload
        parts = token.split(".")
        parts[1] = parts[1][:-4] + "XXXX"
        tampered = ".".join(parts)
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(tampered)

    def test_expired_token_rejected_by_decode(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["admin"],
            ttl_minutes=-1,  # Already expired
        )
        token = encode_token(claims)
        with pytest.raises(ValueError, match="Invalid token"):
            decode_token(token)


class TestTokenClaims:
    def test_user_token_24h_ttl(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["operator"],
            token_type="user",
        )
        delta = claims.exp - claims.iat
        assert 1439 <= delta.total_seconds() / 60 <= 1441

    def test_agent_token_15min_ttl(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["operator"],
            token_type="agent",
        )
        delta = claims.exp - claims.iat
        assert 14 <= delta.total_seconds() / 60 <= 16

    def test_custom_ttl(self) -> None:
        claims = create_token_claims(
            subject_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            roles=["admin"],
            ttl_minutes=5,
        )
        delta = claims.exp - claims.iat
        assert 4 <= delta.total_seconds() / 60 <= 6

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
        claims.exp = datetime.now(tz=UTC) - timedelta(hours=1)
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

    def test_auditor_limited_access(self) -> None:
        assert has_permission(["auditor"], "audit", "read")
        assert not has_permission(["auditor"], "memory", "read")

    def test_multiple_roles_union(self) -> None:
        assert has_permission(["viewer", "auditor"], "memory", "read")
        assert has_permission(["viewer", "auditor"], "audit", "read")

    def test_unknown_role_no_permissions(self) -> None:
        assert not has_permission(["nonexistent"], "workflow", "read")

    def test_default_roles_defined(self) -> None:
        assert set(DEFAULT_ROLES.keys()) == {"admin", "operator", "viewer", "auditor"}


class TestWorkOS:
    async def test_sso_callback(self) -> None:
        profile = await handle_sso_callback("test_code_12345678", "client_id")
        assert profile.email == "user@example.com"
        assert profile.workos_user_id.startswith("workos_")

    async def test_scim_user_created(self) -> None:
        result = await handle_scim_event(
            "dsync.user.created", {"email": "new@example.com"}
        )
        assert result["action"] == "provision"

    async def test_scim_user_deleted(self) -> None:
        result = await handle_scim_event(
            "dsync.user.deleted", {"email": "gone@example.com"}
        )
        assert result["action"] == "deprovision"

    async def test_scim_unknown_event(self) -> None:
        result = await handle_scim_event("unknown.event", {})
        assert result["action"] == "ignored"
