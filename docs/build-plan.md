# Build Plan: Helix Enterprise Agent Orchestration Platform

**Date:** 2026-03-31
**Architecture:** See `docs/architecture.md`
**Total Phases:** 6 | **Estimated Tasks:** 28

---

## Phase 0: Scaffold
**Goal:** Project structure, dependencies, config, linting, CI-ready skeleton.
**Complexity:** S

### Tasks
1. Initialize project with `uv init --lib` using src layout: `src/helix/`
2. Create `pyproject.toml` with all dependencies:
   - Core: `fastapi`, `uvicorn`, `pydantic>=2.9`, `sqlalchemy[asyncio]>=2.0`, `asyncpg`, `alembic`, `redis[hiredis]`, `celery[redis]`, `httpx`
   - AI: `langgraph>=0.3`, `pydantic-ai`, `anthropic`, `openai`
   - Auth: `workos-python`, `python-jose[cryptography]`
   - Integrations: `composio-core`
   - Observability: `structlog`, `sentry-sdk[fastapi]`, `opentelemetry-api`
   - Dev: `pytest`, `pytest-asyncio`, `ruff`, `mypy`, `factory-boy`, `testcontainers[postgres,redis]`
3. Create directory structure:
   ```
   src/helix/
   ├── __init__.py
   ├── main.py              # FastAPI app factory
   ├── config.py             # Pydantic Settings from env vars
   ├── db/
   │   ├── __init__.py
   │   ├── engine.py         # async SQLAlchemy engine
   │   ├── models.py         # SQLAlchemy ORM models
   │   └── migrations/       # Alembic
   ├── api/
   │   ├── __init__.py
   │   ├── deps.py           # FastAPI dependencies (auth, tenant, db session)
   │   ├── routes/
   │   │   ├── __init__.py
   │   │   ├── orgs.py
   │   │   ├── workflows.py
   │   │   ├── agents.py
   │   │   ├── memory.py
   │   │   ├── integrations.py
   │   │   ├── approvals.py
   │   │   └── audit.py
   │   └── middleware/
   │       ├── __init__.py
   │       ├── auth.py        # JWT validation + WorkOS
   │       ├── tenant.py      # org_id extraction + RLS
   │       └── audit.py       # auto-log state changes
   ├── orchestration/
   │   ├── __init__.py
   │   ├── coordinator.py     # LangGraph supervisor agent
   │   ├── workers.py         # Worker agent factory
   │   ├── state.py           # WorkflowState Pydantic model
   │   ├── approval.py        # HITL FSM + escalation
   │   └── speculation.py     # Predictive workflow engine
   ├── memory/
   │   ├── __init__.py
   │   ├── store.py           # Memory CRUD + vector search
   │   ├── dream.py           # 4-phase consolidation cycle
   │   ├── embeddings.py      # Embedding generation
   │   └── pii.py             # PII detection + stripping
   ├── llm/
   │   ├── __init__.py
   │   ├── gateway.py         # Multi-provider router
   │   ├── fallback.py        # Model fallback policies
   │   ├── compaction.py      # 3-layer context compaction
   │   └── metering.py        # Token usage tracking
   ├── integrations/
   │   ├── __init__.py
   │   ├── bus.py             # Integration tool dispatch
   │   ├── registry.py        # Tool registry + risk classification
   │   ├── composio.py        # Composio connector adapter
   │   └── webhooks.py        # Inbound event handler
   ├── auth/
   │   ├── __init__.py
   │   ├── workos.py          # WorkOS SSO/SCIM
   │   ├── rbac.py            # Permission checker
   │   └── tokens.py          # JWT issue/verify
   └── workers/
       ├── __init__.py
       ├── celery_app.py      # Celery configuration
       ├── dream_tasks.py     # Dream cycle Celery tasks
       └── workflow_tasks.py  # Workflow execution tasks
   tests/
   ├── conftest.py            # Fixtures: test DB, Redis, factory instances
   ├── test_config.py
   ├── test_models/
   ├── test_orchestration/
   ├── test_memory/
   ├── test_llm/
   ├── test_integrations/
   └── test_api/
   ```
4. Create `src/helix/config.py` with Pydantic Settings loading all env vars from architecture doc
5. Create `Dockerfile` (multi-stage: build + slim runtime) and `docker-compose.yml` (app + postgres + redis)
6. Configure `ruff` (format + lint) and `mypy` in `pyproject.toml`

### Test Gate
```bash
uv run ruff check src/ && uv run mypy src/helix/config.py && uv run pytest tests/test_config.py -v
```

---

## Phase 1: Core Models & Database
**Goal:** All SQLAlchemy models, Alembic migrations, Pydantic schemas, tenant isolation via RLS.
**Complexity:** M

### Tasks
1. Create SQLAlchemy ORM models in `src/helix/db/models.py` for all tables from architecture:
   - `Org`, `User`, `RolePermission` (tenant foundation)
   - `Workflow`, `WorkflowTemplate`, `Agent`, `AgentMessage` (orchestration)
   - `ApprovalRequest`, `ApprovalPolicy` (HITL)
   - `MemoryRecord`, `DreamRun`, `DreamConfig` (memory)
   - `Integration`, `IntegrationToolExecution` (integration bus)
   - `TokenUsageEvent`, `WorkflowCompactionSnapshot` (LLM gateway)
   - `SpeculativeExecution` (predictive engine)
   - `AuditEvent` (audit trail)
2. Create Alembic initial migration with RLS policies, partitioning on `audit_events`, pgvector extension, indexes
3. Create Pydantic v2 request/response schemas in `src/helix/api/schemas/` for each resource
4. Create `src/helix/db/engine.py` with async SQLAlchemy engine, session factory, and tenant-scoped session dependency
5. Write model tests with `testcontainers[postgres]`: verify RLS isolation, FK constraints, unique constraints, vector columns

### Test Gate
```bash
uv run alembic upgrade head && uv run pytest tests/test_models/ -v --tb=short
```

---

## Phase 2: Orchestration Engine
**Goal:** LangGraph-based coordinator → worker orchestration with HITL approval FSM.
**Complexity:** L

### Tasks
1. Create `src/helix/orchestration/state.py` — `WorkflowState` Pydantic model with FSM phases: `PLANNING → EXECUTING → AWAITING_APPROVAL → VERIFYING → COMPLETE | FAILED`
2. Create `src/helix/orchestration/coordinator.py` — LangGraph `StateGraph` implementing:
   - Supervisor node that plans and spawns worker agents
   - Worker delegation with configurable parallelism
   - Message passing via `agent_messages` table + Redis pub/sub
   - Hierarchy depth enforcement (max 2 levels default, from architecture decision #7)
3. Create `src/helix/orchestration/workers.py` — Worker agent factory using `langgraph.prebuilt.create_react_agent` with injected tool sets per worker role (researcher, implementer, verifier)
4. Create `src/helix/orchestration/approval.py` — Human-in-the-loop approval FSM:
   - `AWAITING_APPROVAL` state with SLA timer
   - Escalation chain when SLA expires
   - Multi-party approval for CRITICAL actions
   - WebSocket notification to clients
5. Create `src/helix/orchestration/speculation.py` — Predictive workflow engine:
   - On approval pending, fork speculative execution in DB savepoint
   - Pre-compute likely next phase (assume APPROVED)
   - On approval: `RELEASE SAVEPOINT`, apply queued writes
   - On rejection: `ROLLBACK TO SAVEPOINT`
6. Write orchestration tests: workflow lifecycle, approval flow, speculation apply/discard, hierarchy depth enforcement

### Test Gate
```bash
uv run pytest tests/test_orchestration/ -v --tb=short -k "test_workflow_lifecycle or test_approval_flow or test_speculation"
```

---

## Phase 3: Memory System (Dream Cycle)
**Goal:** Institutional memory with vector storage, semantic retrieval, and 4-phase consolidation.
**Complexity:** L

### Tasks
1. Create `src/helix/memory/store.py` — Memory CRUD:
   - `create_memory()`, `retrieve_relevant()` (vector similarity), `update_memory()`, `invalidate_memory()`
   - `retrieve_relevant()` uses `SELECT ... ORDER BY embedding <=> $query_vec LIMIT 10` (architecture decision #4)
   - Access control: filter by `access_level` and `allowed_roles` based on requesting agent/user role
2. Create `src/helix/memory/embeddings.py` — Embedding generation via OpenAI `text-embedding-3-large` or Haiku, with async batching
3. Create `src/helix/memory/pii.py` — PII detection + stripping pass (regex-based for speed, like Claude Code's regex sentiment — zero-cost, deterministic)
4. Create `src/helix/memory/dream.py` — 4-phase Dream Cycle (adapted from autoDream):
   - **Orient**: Query existing memory index for org
   - **Gather**: Fetch session transcripts since last run, extract signals via Haiku (corrections, decisions, recurring themes)
   - **Consolidate**: Merge/deduplicate via Sonnet, generate embeddings, strip PII, write to `memory_records`
   - **Prune**: Enforce `max_memory_records` per org, invalidate stale records, update `dream_runs` log
   - Three-gate trigger: configurable `min_hours` + `min_sessions` + Redis distributed lock
5. Create Celery task `src/helix/workers/dream_tasks.py` — scheduled trigger check every 15 min, dispatch dream cycle per qualifying org
6. Write memory tests: vector retrieval accuracy, access control enforcement, dream cycle full flow, PII stripping

### Test Gate
```bash
uv run pytest tests/test_memory/ -v --tb=short -k "test_retrieval or test_dream_cycle or test_pii_strip or test_access_control"
```

---

## Phase 4: LLM Gateway & Integration Bus
**Goal:** Multi-provider LLM routing with fallback policies, context compaction, and SaaS integration connectors.
**Complexity:** M

### Tasks
1. Create `src/helix/llm/gateway.py` — Multi-provider async LLM router:
   - Provider selection from `LLMPolicy` per org
   - Streaming support via `httpx` + PydanticAI structured outputs
   - Circuit breaker: 3 consecutive failures → mark provider down for 60s
   - Per-tenant rate limiting via Redis token bucket
2. Create `src/helix/llm/fallback.py` — Model fallback policies:
   - Configurable cascade chain per org (default: Opus → Sonnet → Haiku)
   - Transparent fallback: emit `model_fallback` audit event with reason
   - `allow_silent_downgrade` flag per org (architecture decision #5)
3. Create `src/helix/llm/compaction.py` — 3-layer context compaction (from Claude Code's query engine):
   - Micro-compaction: offload tool outputs > 8KB threshold to S3, replace with reference
   - Auto-compaction: fire at 83.5% context, produce structured summary (intent, decisions, artifacts, pending, next steps)
   - Cross-session compaction: inject compaction snapshot when resuming interrupted workflows
4. Create `src/helix/llm/metering.py` — Token usage tracking: write `token_usage_events` per LLM call with `(org_id, workflow_id, agent_id, model_id, cost_usd)`
5. Create `src/helix/integrations/bus.py` + `registry.py` — Tool dispatch:
   - Risk classification lookup per tool per tenant
   - Approval routing for HIGH/CRITICAL actions
   - Concurrent reads, serial writes (from Claude Code's tool dispatch pattern)
   - Per-integration rate limiting via Redis
6. Write gateway + integration tests: fallback cascade, circuit breaker, compaction trigger, rate limiting, tool dispatch with approval routing

### Test Gate
```bash
uv run pytest tests/test_llm/ tests/test_integrations/ -v --tb=short
```

---

## Phase 5: API Layer & Auth
**Goal:** FastAPI routes, WorkOS SSO, RBAC middleware, WebSocket for approvals, audit middleware.
**Complexity:** M

### Tasks
1. Create `src/helix/auth/workos.py` — WorkOS SSO callback handler, SCIM webhook processor, user provisioning
2. Create `src/helix/auth/rbac.py` — Permission checker: `has_permission(user_or_agent_id, resource, action, conditions)` evaluating `role_permissions` table
3. Create `src/helix/auth/tokens.py` — JWT issue (RS256) for users and short-lived agent tokens (15-min TTL)
4. Create API routes in `src/helix/api/routes/`:
   - `orgs.py`: CRUD orgs, onboarding flow
   - `workflows.py`: create, get, list, cancel workflows
   - `agents.py`: list agents per workflow, get agent trace
   - `memory.py`: query memory (vector search), manual create/invalidate
   - `integrations.py`: add/remove integrations, OAuth flow, list tools
   - `approvals.py`: list pending, approve/reject, escalation status
   - `audit.py`: query audit trail, integrity verification endpoint
5. Create `src/helix/api/middleware/audit.py` — Auto-log all state-changing requests to `audit_events`
6. Create WebSocket endpoint for real-time approval notifications and workflow status streaming

### Test Gate
```bash
uv run pytest tests/test_api/ -v --tb=short && uv run ruff check src/ && uv run mypy src/
```

---

## Phase 6: Hardening & Deployment
**Goal:** Docker, Helm, observability, error handling, load testing, documentation.
**Complexity:** M

### Tasks
1. Finalize `Dockerfile` (multi-stage) and `docker-compose.yml` with healthchecks for all services
2. Create Helm chart in `deploy/helm/helix/` with templates for: API deployment, Celery workers (2 pools: workflow + dream), PostgreSQL (external), Redis (external), ConfigMaps for env vars, Secrets for credentials
3. Add OpenTelemetry instrumentation: traces on all LLM calls, spans on workflow phases, metrics on token usage and approval latency
4. Add Sentry error tracking with `structlog` integration
5. Create `scripts/load_test.py` — Locust or k6 load test: concurrent workflow creation, approval flow, memory queries
6. Final `ruff format`, `mypy --strict`, security audit (no hardcoded secrets, no SQL injection, no prompt injection vectors)

### Test Gate
```bash
docker compose up -d && docker compose exec api uv run pytest tests/ -v --tb=short && docker compose down
```

---

## Phase Summary

| Phase | Name | Tasks | Complexity | Key Deliverable |
|---|---|---|---|---|
| 0 | Scaffold | 6 | S | Project skeleton, deps, Docker |
| 1 | Core Models | 5 | M | DB schema, RLS, Pydantic schemas |
| 2 | Orchestration | 6 | L | LangGraph coordinator, HITL, speculation |
| 3 | Memory System | 6 | L | Dream cycle, vector search, PII stripping |
| 4 | LLM + Integrations | 6 | M | Multi-provider gateway, SaaS connectors |
| 5 | API + Auth | 6 | M | FastAPI routes, WorkOS SSO, RBAC |
| 6 | Hardening | 6 | M | Docker, Helm, observability, load tests |

**Critical path:** Phase 0 → Phase 1 → (Phase 2 + Phase 3 in parallel) → Phase 4 → Phase 5 → Phase 6

Phases 2 and 3 can be built in parallel since orchestration and memory are independent until integration in Phase 4.
