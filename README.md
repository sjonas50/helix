# Helix

**Enterprise AI Agent Orchestration Platform**

Helix is the orchestration layer that sits between your enterprise SaaS tools and AI agents. It automates multi-step workflows across Salesforce, Jira, Slack, and 7 other enterprise systems — with institutional memory that compounds over time, human-in-the-loop approval gates, and the security controls enterprise customers require.

Two intertwined strands: **orchestration** and **memory**.

---

## Why Helix

| Problem | Helix Solution |
|---|---|
| Salesforce costs $150-300/user/month | AI agents automate the workflows, not replace the CRM |
| Teams copy-paste between 5+ SaaS tools | Agents orchestrate across systems automatically |
| AI agents make mistakes on critical data | Human-in-the-loop gates on every write operation |
| Institutional knowledge lives in people's heads | Dream Cycle consolidates memory across sessions |
| Enterprise security requirements | JWT auth, RBAC, RLS on every table, SOC 2 audit trail |

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HELIX PLATFORM                               │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                     CONTROL PLANE                              │ │
│  │  FastAPI  ·  JWT Auth  ·  RBAC  ·  Tenant Isolation  ·  Audit │ │
│  └──────────────────────┬─────────────────────────────────────────┘ │
│                         │                                           │
│  ┌──────────────────────▼─────────────────────────────────────────┐ │
│  │                 ORCHESTRATION ENGINE                            │ │
│  │  LangGraph StateGraph  ·  Coordinator → Worker Agents          │ │
│  │  Human-in-the-Loop Approval  ·  Speculative Pre-computation    │ │
│  └────────┬───────────────────────────────────────┬───────────────┘ │
│           │                                       │                 │
│  ┌────────▼──────────┐              ┌─────────────▼───────────────┐ │
│  │   LLM GATEWAY     │              │    INTEGRATION BUS          │ │
│  │  Claude + OpenAI   │              │  10 Enterprise Providers    │ │
│  │  Circuit Breaker   │              │  45+ Tools · Risk Levels    │ │
│  │  Cost Metering     │              │  Nango Auth + Direct APIs   │ │
│  └────────┬──────────┘              └─────────────┬───────────────┘ │
│           │                                       │                 │
│  ┌────────▼───────────────────────────────────────▼───────────────┐ │
│  │                  MEMORY & STATE                                 │ │
│  │  PostgreSQL + pgvector  ·  Redis  ·  Celery                    │ │
│  │  Dream Cycle (4-phase consolidation)  ·  Semantic Search       │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Features

### Orchestration Engine
- **LangGraph StateGraph** with typed state and compiled workflow: `plan → execute → approve → verify`
- **Multi-agent coordination** with role-based tool assignment (researcher, implementer, verifier)
- **Human-in-the-loop** approval as a first-class FSM state with SLA escalation
- **Speculative pre-computation** — pre-executes likely next steps while awaiting approval; instant on approval, discarded on rejection
- **Configurable agent hierarchy** (depth 2 default, max 4) — not hard-coded like Claude Code's single level

### Institutional Memory (Dream Cycle)
- **4-phase consolidation** adapted from Claude Code's autoDream: Orient → Gather → Consolidate → Prune
- **Semantic search** via pgvector cosine similarity — one DB round-trip, not sequential file reads
- **Org-scoped memory** with role-based access control (PUBLIC / ROLE_RESTRICTED / CONFIDENTIAL)
- **PII stripping** before embedding (regex-based, zero-cost — same philosophy as Claude Code's regex sentiment)
- **Configurable triggers** per org (default: 24hr + 5 sessions + Redis distributed lock)
- **LLM-powered Gather phase** — Haiku extracts corrections, decisions, and themes from recent memory

### Ambient Memory Pipeline
- **Webhook ingest** — Slack messages, Jira issues, GitHub PRs flow into memory automatically
- **Normalize → hash → embed → upsert** — structured pipeline per provider
- **Content hash dedup** — SHA-256 prevents duplicate embeddings on repeated events
- **Source tracking** — every memory record knows its `source_system`, `source_id`, and `source_url`
- **ON CONFLICT upsert** — updated records replace old embeddings, not create duplicates

### LLM Gateway
- **Multi-provider**: Anthropic (primary), OpenAI (fallback), Azure/Bedrock ready
- **Circuit breaker** at 3 consecutive failures with cooldown (matches Claude Code's threshold)
- **Transparent fallback** with audit events — not silent downgrades (arch decision #5)
- **3-layer context compaction**: micro (8KB), auto (83.5%), cross-session resume
- **Token metering** with per-org cost attribution and billing tracking
- **Structured outputs** via PydanticAI for type-safe LLM extraction

### Enterprise Integrations

| Provider | Tools | Risk Range | Category |
|---|---|---|---|
| **Salesforce** | get_account, list_opportunities, update_opportunity, create_contact, delete_account | LOW — CRITICAL | CRM |
| **Slack** | send_message, list_channels, search_messages, create_channel, invite_to_channel | LOW — MEDIUM | Communication |
| **Jira** | get_issue, list_issues, create_issue, update_issue, transition_issue | LOW — HIGH | Project Management |
| **Google Workspace** | send_email, create_doc, list_files, create_event, share_file | LOW — HIGH | Productivity |
| **HubSpot** | get_contact, list_deals, create_contact, update_deal, create_task | LOW — HIGH | CRM |
| **ServiceNow** | get_incident, list_incidents, create_incident, update_incident, assign_incident | LOW — HIGH | ITSM |
| **Zendesk** | get_ticket, list_tickets, create_ticket, update_ticket, add_comment | LOW — MEDIUM | Helpdesk |
| **GitHub** | get_issue, list_prs, create_issue, create_pr, merge_pr | LOW — CRITICAL | DevOps |
| **Notion** | search_pages, get_page, create_page, update_page, add_to_database | LOW — MEDIUM | Knowledge |
| **DocuSign** | get_envelope_status, list_envelopes, send_envelope, void_envelope | LOW — CRITICAL | eSign |

### Agent Skills

| Skill | Category | Integrations Used |
|---|---|---|
| `summarize_thread` | Ops | Slack, Google Workspace |
| `draft_email` | Sales | Salesforce, Google Workspace |
| `score_lead` | Sales | Salesforce, HubSpot |
| `create_report` | Ops | Salesforce, Google Workspace |
| `route_ticket` | Support | Zendesk, Slack |
| `schedule_meeting` | Ops | Google Workspace, Slack |
| `onboard_user` | HR | Slack, Jira, GitHub |
| `detect_churn_risk` | Support | Salesforce, Zendesk |
| `process_invoice` | Finance | Google Workspace, Slack |
| `incident_response` | DevOps | ServiceNow, Slack, Google Workspace |

### Security

- **JWT authentication** (HS256 dev / RS256 production) on every endpoint
- **4 RBAC roles**: admin (wildcard), operator, viewer, auditor
- **Row Level Security** on 17 tenant-scoped PostgreSQL tables
- **Append-only audit trail** with chain hashing for tamper detection
- **Agent tokens**: 15-minute TTL — never long-lived credentials
- **PII stripping** in memory consolidation pipeline
- **Webhook signature verification** (HMAC-SHA256)
- **Tool outputs treated as untrusted** — sanitized before agent context injection

## Tech Stack

| Layer | Technology |
|---|---|
| **API** | FastAPI + Pydantic v2 |
| **Orchestration** | LangGraph (StateGraph + compiled workflows) |
| **LLM** | Claude Sonnet 4.6 (primary), Haiku 4.5 (routing), Opus 4.6 (planning) |
| **Structured Output** | PydanticAI |
| **Database** | PostgreSQL 16 + pgvector |
| **Cache / Pub-Sub** | Redis 7 |
| **Background Tasks** | Celery (workflow + dream queues) |
| **Auth/Integrations** | Nango (OAuth) + direct API calls via httpx |
| **Auth** | WorkOS (SSO/SCIM) + python-jose (JWT) |
| **Observability** | structlog + Sentry + OpenTelemetry |
| **Deployment** | Docker + Helm |

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/) package manager

### 1. Clone and install

```bash
git clone https://github.com/sjonas50/helix.git
cd helix
cp .env.example .env  # Edit with your API keys
uv sync --dev
```

### 2. Start infrastructure

```bash
docker compose up -d postgres redis
```

### 3. Run migrations

```bash
uv run alembic upgrade head
```

### 4. Start the API

```bash
uv run uvicorn helix.main:app --reload
```

### 5. Start background workers (separate terminals)

```bash
# Workflow execution queue (high priority)
uv run celery -A helix.workers.celery_app worker -Q workflow -l info

# Dream cycle queue (low priority, separate pool)
uv run celery -A helix.workers.celery_app worker -Q dream -l info

# Beat scheduler (dream triggers every 15 min)
uv run celery -A helix.workers.celery_app beat -l info
```

### 6. Verify

```bash
curl http://localhost:8000/health
# {"status": "ok"}

# Run the test suite
uv run pytest tests/ -v
# 322 passed
```

### Full stack with Docker Compose

```bash
docker compose up -d
# Starts: api, worker-workflow, worker-dream, beat, postgres, redis
```

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | No | Health check |
| `POST` | `/api/v1/orgs/` | Yes | Create organization |
| `GET` | `/api/v1/orgs/{id}` | Yes | Get organization |
| `POST` | `/api/v1/workflows/` | Yes | Create workflow |
| `GET` | `/api/v1/workflows/` | Yes | List workflows |
| `GET` | `/api/v1/workflows/{id}` | Yes | Get workflow status |
| `GET` | `/api/v1/agents/workflow/{id}` | Yes | List agents in workflow |
| `GET` | `/api/v1/agents/{id}` | Yes | Get agent details |
| `GET` | `/api/v1/agents/{id}/messages` | Yes | Get agent messages |
| `POST` | `/api/v1/memory/` | Yes | Create memory record |
| `POST` | `/api/v1/memory/search` | Yes | Semantic memory search |
| `GET` | `/api/v1/memory/dream-runs` | Yes | List Dream Cycle runs |
| `POST` | `/api/v1/memory/dream-runs/trigger` | Yes | Trigger Dream Cycle |
| `POST` | `/api/v1/integrations/` | Yes | Add integration |
| `GET` | `/api/v1/integrations/` | Yes | List integrations |
| `GET` | `/api/v1/integrations/providers` | Yes | List supported providers |
| `GET` | `/api/v1/integrations/{id}/tools` | Yes | List integration tools |
| `GET` | `/api/v1/approvals/` | Yes | List pending approvals |
| `POST` | `/api/v1/approvals/{id}/decide` | Yes | Approve/reject action |
| `GET` | `/api/v1/audit/events` | Yes | Query audit trail |
| `GET` | `/api/v1/audit/integrity` | Yes | Verify audit chain |
| `GET` | `/api/v1/usage/stats` | Yes | Token usage statistics |
| `WS` | `/api/v1/ws?token=<jwt>` | Yes | Real-time notifications (org from JWT) |

## Project Structure

```
helix/
├── src/helix/
│   ├── main.py                    # FastAPI app factory
│   ├── config.py                  # Pydantic Settings (env vars)
│   ├── observability.py           # structlog + Sentry + OpenTelemetry
│   ├── api/
│   │   ├── routes/                # 9 route modules (25 endpoints)
│   │   ├── middleware/            # auth, tenant isolation, audit
│   │   ├── schemas/               # Pydantic request/response models
│   │   └── deps.py               # FastAPI dependencies
│   ├── orchestration/
│   │   ├── coordinator.py         # LangGraph StateGraph + node functions
│   │   ├── state.py              # WorkflowState FSM (6 phases)
│   │   ├── workers.py            # Worker agent factory + tool registry
│   │   ├── approval.py           # HITL approval with SLA escalation
│   │   ├── speculation.py        # Speculative pre-computation
│   │   └── ipc.py                # DB-backed inter-agent messaging
│   ├── memory/
│   │   ├── store.py              # Memory CRUD + pgvector search
│   │   ├── dream.py              # 4-phase Dream Cycle
│   │   ├── embeddings.py         # OpenAI embedding generation
│   │   └── pii.py                # PII detection + stripping
│   ├── llm/
│   │   ├── gateway.py            # Multi-provider router + circuit breaker
│   │   ├── compaction.py         # 3-layer context compaction
│   │   ├── metering.py           # Token usage persistence
│   │   └── structured.py         # PydanticAI structured outputs
│   ├── integrations/
│   │   ├── registry.py           # 10 providers, 45+ tools
│   │   ├── skills.py             # 10 agent skills
│   │   ├── bus.py                # Tool dispatch + risk classification
│   │   ├── nango.py              # Nango OAuth + direct API execution
│   │   ├── ingest.py             # Webhook → normalize → embed → upsert pipeline
│   │   ├── composio.py           # Composio SDK adapter (legacy reference)
│   │   └── webhooks.py           # Inbound event handler
│   ├── auth/
│   │   ├── tokens.py             # JWT signing/verification
│   │   ├── rbac.py               # Role-based access control
│   │   └── workos.py             # WorkOS SSO/SCIM
│   ├── memory/
│   │   ├── store.py              # Memory CRUD + pgvector search
│   │   ├── dream.py              # 4-phase Dream Cycle
│   │   ├── gather.py             # LLM-powered signal extraction (Haiku)
│   │   ├── embeddings.py         # OpenAI embedding generation
│   │   └── pii.py                # PII detection + stripping
│   ├── workers/
│   │   ├── celery_app.py         # Celery config (2 queues)
│   │   ├── dream_tasks.py        # Dream Cycle Celery tasks (wired to real DB + LLM)
│   │   └── ingest_tasks.py       # Webhook ingest Celery tasks
│   └── db/
│       ├── models.py             # 19 SQLAlchemy ORM models
│       ├── engine.py             # Async engine singleton
│       └── migrations/           # Alembic (pgvector + RLS)
├── tests/                         # 322 backend + 87 frontend tests
├── deploy/helm/helix/             # Kubernetes Helm chart
├── scripts/load_test.py           # Async load testing
├── docker-compose.yml             # 6 services
├── Dockerfile                     # Multi-stage build
├── CLAUDE.md                      # AI-assisted development instructions
└── docs/
    ├── architecture.md            # Full system architecture
    ├── build-plan.md              # Original build plan (phases 0-6)
    ├── build-plan-v2.md           # Extended build plan (phases 7-14)
    └── research.md                # Claude Code analysis + CRM research
```

## Architecture Decisions

These decisions are informed by analysis of Anthropic's Claude Code production system (512K lines, leaked March 2026):

| # | Decision | Claude Code Pattern | Our Improvement |
|---|---|---|---|
| 1 | LangGraph over custom FSM | Custom TypeScript state machine | Production state machine with persistence + interrupt/resume |
| 2 | PostgreSQL IPC over file-based | `~/.claude/teams/` file lock IPC | Distributed, durable, no file lock races |
| 3 | DB savepoints for speculation | Overlay filesystem sandbox | ACID-safe, distributed, no escape vulnerability |
| 4 | pgvector over keyword matching | Sonnet reads 5 files sequentially | O(log N) semantic similarity in one DB query |
| 5 | Transparent model fallback | Silent Opus → Sonnet downgrade | Audit events, configurable per org |
| 6 | RLS as defense-in-depth | No tenant isolation (single-user) | Even SQL injection can't cross tenant boundaries |
| 7 | Configurable hierarchy depth | Hard-coded 1 level | Default 2, max 4, enforced in engine not prompt |
| 8 | Nango for OAuth + direct API calls | Composio cloud (vendor lock-in, no self-host) | Token ownership, on-prem safe, httpx for execution |
| 9 | Append-only audit with chain hash | No audit trail | SOC 2 tamper detection |
| 10 | Separate Celery queues | Forked subagent in main process | Dream cycle never blocks real-time workflows |

## Environment Variables

```bash
# Core
ENVIRONMENT=production              # development | staging | production
SECRET_KEY=                         # 32+ char random string (required)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/helix
REDIS_URL=redis://host:6379/0

# LLM Providers
ANTHROPIC_API_KEY=                  # Primary LLM provider
OPENAI_API_KEY=                     # Fallback + embeddings

# Identity
WORKOS_API_KEY=                     # Enterprise SSO
WORKOS_CLIENT_ID=
WORKOS_WEBHOOK_SECRET=

# Integrations
COMPOSIO_API_KEY=                   # Managed SaaS connectors

# Observability
SENTRY_DSN=                         # Error tracking
OTEL_EXPORTER_OTLP_ENDPOINT=       # Distributed tracing
LOG_LEVEL=INFO
```

See `.env.example` for the full list.

## Development

```bash
# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest tests/ -v

# Lint + format
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/

# Type check
uv run mypy src/

# Run migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "description"

# Load test
python scripts/load_test.py --base-url http://localhost:8000 --concurrency 50
```

## Deployment

### Docker Compose (development/staging)

```bash
docker compose up -d
```

### Kubernetes (production)

```bash
helm install helix deploy/helm/helix/ \
  --set secrets.SECRET_KEY="$(openssl rand -hex 32)" \
  --set secrets.ANTHROPIC_API_KEY="sk-ant-..." \
  --set secrets.OPENAI_API_KEY="sk-..." \
  --set env.DATABASE_URL="postgresql+asyncpg://..." \
  --set env.REDIS_URL="redis://..." \
  --set ingress.enabled=true \
  --set ingress.host=helix.yourdomain.com
```

## License

Proprietary. All rights reserved.
