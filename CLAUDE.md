# Helix — Enterprise AI Agent Orchestration Platform

## What This Is
Multi-tenant platform providing AI agent orchestration and institutional memory for enterprise customers. Agents automate workflows across SaaS tools (Salesforce, Jira, Slack, SAP) with RBAC, audit trails, and human-in-the-loop approval gates.

Architecture is directly informed by Anthropic's Claude Code (Tengu) production system. See `docs/architecture.md` for the full mapping.

## Stack
- **Python 3.11+** with `uv` for package management
- **FastAPI + Pydantic v2** — API + validation
- **LangGraph** — Agent orchestration state machines
- **PydanticAI** — Structured LLM outputs
- **Claude API** — Sonnet 4.6 (primary), Haiku 4.5 (routing/classification), Opus 4.6 (complex planning)
- **PostgreSQL 16 + pgvector** — Data + vector embeddings
- **Redis** — Cache, pub/sub, rate limiting, task queues
- **Celery** — Background workers (dream cycle, workflow execution)
- **Composio/Nango** — SaaS integration connectors
- **WorkOS** — Enterprise SSO/SCIM
- **Docker + Helm** — Deployment

## Commands
```bash
# Install
uv sync

# Run
uv run uvicorn src.helix.main:app --reload

# Test
uv run pytest tests/ -v

# Lint + Format
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type check
uv run mypy src/

# Migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"

# Celery workers
uv run celery -A src.helix.workers.celery_app worker -Q workflow -l info
uv run celery -A src.helix.workers.celery_app worker -Q dream -l info
uv run celery -A src.helix.workers.celery_app beat -l info
```

## Architecture Decisions (Key)
1. LangGraph over custom FSM — production state machine with persistence + interrupt/resume
2. PostgreSQL IPC over file-based messages — distributed, durable, no file lock races
3. DB savepoints over overlay filesystem for speculation — ACID-safe, distributed
4. pgvector semantic retrieval over keyword matching — O(log N) vs O(N), catches concept matches
5. Transparent model fallback over silent downgrades — audit events, configurable per org
6. RLS as defense-in-depth — even SQL injection can't cross tenant boundaries
7. Configurable agent hierarchy depth (default 2, max 4) — Claude Code hard-codes 1 level
8. Composio/Nango for integrations — 250+ managed connectors vs building OAuth from scratch
9. Append-only audit trail with chain hashing — SOC 2 tamper detection
10. Separate Celery queues for real-time vs background — dream cycle never blocks workflows

## Project Structure
```
src/helix/
├── main.py              # FastAPI app factory
├── config.py            # Pydantic Settings
├── db/                  # SQLAlchemy models, Alembic migrations
├── api/                 # Routes, middleware, schemas
├── orchestration/       # LangGraph coordinator, workers, HITL, speculation
├── memory/              # Dream cycle, vector store, PII stripping
├── llm/                 # Multi-provider gateway, fallback, compaction, metering
├── integrations/        # Tool dispatch, Composio adapter, webhooks
├── auth/                # WorkOS SSO, RBAC, JWT
└── workers/             # Celery tasks (workflow + dream)
```

## Pitfalls to Avoid (from research)
- **Never silent-downgrade models without audit event** — SOC 2 requirement
- **Always scope DB queries by org_id** — RLS is backup, not primary defense
- **Agent tokens are 15-min TTL** — never issue long-lived agent credentials
- **Dream cycle runs in separate Celery queue** — never compete with real-time workflows
- **Tool outputs are UNTRUSTED** — sanitize before injecting into agent context (prompt injection defense)
- **Speculation only allows read-only integration calls** — writes queued until confirmation
- **Pin PydanticAI version** — pre-1.0, API may break
- **Anthropic Tier 1 rate limit is 50 RPM** — need spend history to unlock Tier 2, start early
