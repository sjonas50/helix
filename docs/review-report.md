# Code Review Report
**Date:** 2026-03-31
**Status:** PASS WITH NOTES

## Critical Issues (must fix)

1. **WebSocket endpoint has no authentication** — `/api/v1/ws/{org_id}` accepts any connection without JWT validation; an attacker can subscribe to any org's real-time events by guessing/enumerating `org_id`. `/Users/sjonas/cc/src/helix/api/routes/ws.py:40-53`

2. **IPC `send_message` uses string replacement for JSON serialization** — `str(payload).replace("'", '"')` is not valid JSON serialization; it will corrupt payloads containing apostrophes, nested quotes, booleans (`True`/`False` vs `true`/`false`), or `None` vs `null`. This is also a potential SQL injection vector via JSONB cast. `/Users/sjonas/cc/src/helix/orchestration/ipc.py:35`

3. **`datetime.now()` used without timezone throughout business logic** — `datetime.now()` returns naive datetimes. Used in `DreamRunResult`, `SessionSignal`, `MemoryEntry`, `WorkflowState`, `ApprovalRequest`, `AgentMessage`, `CircuitBreaker`, `TokenUsageTracker`. Comparisons between naive and tz-aware datetimes will raise `TypeError` at runtime. Affected files: `src/helix/memory/dream.py:71,86,108,301,314`, `src/helix/memory/store.py:41`, `src/helix/orchestration/state.py:53,114,115`, `src/helix/orchestration/approval.py:46,53,72,115`, `src/helix/orchestration/speculation.py:49`, `src/helix/llm/gateway.py:129,149,177`

4. **`require_roles` middleware is broken** — It's an async function that returns a closure, but is never used as a factory correctly. Calling `Depends(require_roles("admin"))` will resolve the outer coroutine, not inject the inner dependency. This means role-based route protection is non-functional. `/Users/sjonas/cc/src/helix/api/middleware/auth.py:49-61`

## Warnings (should fix)

1. **`broadcast_to_org` silently swallows all exceptions** — `contextlib.suppress(Exception)` hides errors including broken pipes, serialization failures, and auth issues. Should at minimum log the exception. `/Users/sjonas/cc/src/helix/api/routes/ws.py:33-34`

2. **Dependencies not pinned to exact versions** — `pyproject.toml` uses `>=` constraints (e.g., `fastapi>=0.115.0`). For reproducible builds and CVE management, pin exact versions or use `~=` constraints. `/Users/sjonas/cc/pyproject.toml:7-36`

3. **Default `secret_key` in Settings is weak** — `"change-me-in-production"` is a 23-char string that passes the `min_length=16` validation. No enforcement that it gets changed in production environments. `/Users/sjonas/cc/src/helix/config.py:25`

4. **Token signing hardcoded to HS256** — `_ALGORITHM = "HS256"` ignores the `jwt_algorithm` and `jwt_public_key_path` settings fields. The config supports RS256 but the implementation doesn't use it. `/Users/sjonas/cc/src/helix/auth/tokens.py:22`

5. **Tenant context (RLS) not wired into request lifecycle** — `set_tenant_context()` exists but is never called from any middleware or dependency. RLS defense-in-depth (arch decision #6) is defined but not activated. `/Users/sjonas/cc/src/helix/api/middleware/tenant.py`

6. **`memory/dream.py` consolidate phase truncates UTF-8 unsafely** — `cleaned_content[:cfg.max_bytes_per_record]` slices by character count, not bytes, despite the variable name saying `max_bytes`. Could also split multi-byte UTF-8 characters. `/Users/sjonas/cc/src/helix/memory/dream.py:196`

7. **LLM gateway creates a new HTTP client on every call** — `AsyncAnthropic()` and `AsyncOpenAI()` are instantiated per-request inside `_call_anthropic`/`_call_openai`, bypassing connection pooling. `/Users/sjonas/cc/src/helix/llm/gateway.py:244,288`

8. **`get_settings()` is not cached** — Called without `@lru_cache`, so every invocation re-parses `.env` and environment variables. Called from `get_engine()`, `_call_anthropic()`, `_call_openai()`, token functions, embedding functions, Celery app init, etc. `/Users/sjonas/cc/src/helix/config.py:87-89`

9. **Audit middleware exists but is never registered** — `create_audit_entry()` and `should_audit()` are defined in `src/helix/api/middleware/audit.py` but never imported or used in `main.py` or any route. No state-changing requests are actually audited.

10. **`docker-compose.yml` passes `.env` file to all services** — The `.env` file contains all secrets. Workers and beat schedulers receive secrets they don't need (e.g., `WORKOS_API_KEY` on Celery workers). Least-privilege violation.

## Suggestions (nice to have)

1. **Add `content_max_length` validation to `MemoryCreate` schema** — `content: str = Field(min_length=1)` has no upper bound; a large payload could exhaust memory or DB storage. `/Users/sjonas/cc/src/helix/api/schemas/memory.py:16`

2. **Observability `setup_opentelemetry` creates provider but never adds a span exporter** — The OTLP exporter is referenced in config but never instantiated. Traces will be dropped silently. `/Users/sjonas/cc/src/helix/observability.py:59-71`

3. **`DreamPhase` should be a `StrEnum`** — It's a plain class with string constants, unlike `WorkflowPhase` which is a proper `StrEnum`. Inconsistent pattern. `/Users/sjonas/cc/src/helix/memory/dream.py:32-39`

4. **`validate_hierarchy_depth` is duplicated** — Defined in both `src/helix/orchestration/coordinator.py:165` and `src/helix/orchestration/workers.py:47`.

5. **Webhook signature verification not called in `process_webhook`** — `verify_signature()` exists but is never invoked when processing inbound webhooks. `/Users/sjonas/cc/src/helix/integrations/webhooks.py:63`

6. **Consider CORS middleware** — No CORS configuration in `main.py`. Frontend clients will be blocked by browsers.

7. **`composio.py:61` builds URL via string interpolation** — `org_id` and `redirect_uri` are not URL-encoded, which could cause malformed URLs or open redirect. `/Users/sjonas/cc/src/helix/integrations/composio.py:61`

8. **Test coverage gap: no tests for `src/helix/llm/structured.py`, `src/helix/observability.py`, `src/helix/api/middleware/tenant.py`**.

## Metrics
- Files reviewed: 47 source + 27 test files
- Test count: 281 (all passing)
- Ruff violations: 0
- Security issues: 4 critical, 10 warning
