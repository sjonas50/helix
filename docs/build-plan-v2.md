# Build Plan v2: Helix — Wire the I/O & Expand the Platform

**Date:** 2026-03-31
**Status:** Phases 0-5 delivered domain logic + data models. Zero real I/O.
**This plan:** Wire everything to real systems, then expand beyond Salesforce.
**Total New Phases:** 7 (Phases 7-13) | **Estimated Tasks:** 40

---

## Current State

**What works:** 178 tests passing. Config, ORM models (19 tables), workflow FSM with validated transitions, HITL approval lifecycle, speculation scoring, Dream Cycle 4-phase logic, PII stripping, LLM cost calculation, circuit breaker, integration tool risk classification, RBAC permission checks, API route structure.

**What doesn't work:** Nothing talks to a database, LLM, Redis, or external API. No JWT signing. No auth middleware. No Celery workers. No migrations. No embeddings. No WebSocket.

**Bugs fixed:** Engine pool leak (singleton now), RBAC condition evaluation (fall-through fixed).

---

## Phase 7: Database Foundation
**Goal:** Alembic migrations, RLS policies, pgvector setup. Make the DB real.
**Complexity:** M
**Depends on:** docker-compose postgres running

### Tasks
1. Create `alembic.ini` and `src/helix/db/migrations/` with Alembic async config pointing to `DATABASE_URL`
2. Create initial migration — all 19 tables from `models.py`:
   - `CREATE EXTENSION IF NOT EXISTS vector` for pgvector
   - `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` for `gen_random_uuid()`
   - All tables, indexes, unique constraints from ORM models
   - `embedding vector(1536)` column on `memory_records` (raw SQL, not ORM-mapped)
   - IVFFlat index: `CREATE INDEX idx_memory_embedding ON memory_records USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)`
3. Create RLS migration:
   - `ALTER TABLE <table> ENABLE ROW LEVEL SECURITY` on all tenant-scoped tables
   - `CREATE POLICY tenant_isolation ON <table> USING (org_id = current_setting('app.current_org_id')::UUID)`
   - Revoke `DELETE`, `UPDATE` on `audit_events` from app role
   - Range partition `audit_events` by `created_at` (monthly)
4. Create `src/helix/api/middleware/tenant.py` — FastAPI middleware that calls `SET LOCAL app.current_org_id = :org_id` per request using org from JWT claims
5. Write migration tests: `alembic upgrade head` + `alembic downgrade base` roundtrip, RLS isolation verification (insert as org A, query as org B returns nothing)

### Test Gate
```bash
docker compose up -d postgres && uv run alembic upgrade head && uv run pytest tests/test_db/ -v && uv run alembic downgrade base
```

---

## Phase 8: Auth & Security
**Goal:** Real JWT signing, WorkOS SSO, auth middleware. Lock down every endpoint.
**Complexity:** M

### Tasks
1. Implement `src/helix/auth/tokens.py` — Real JWT signing/verification:
   - `encode_token(claims) -> str` using `python-jose` with RS256 (or HS256 for dev)
   - `decode_token(token) -> TokenClaims` with signature verification + expiry check
   - Agent tokens: 15-min TTL, User tokens: 24-hour TTL
2. Create `src/helix/auth/workos.py`:
   - `get_authorization_url()` → WorkOS SSO redirect
   - `handle_callback(code) -> User` → exchange code, upsert user, issue JWT
   - `handle_scim_webhook(payload)` → provision/deprovision users
3. Create `src/helix/api/middleware/auth.py` — FastAPI dependency:
   - Extract `Authorization: Bearer <token>` header
   - Decode + verify JWT → populate `CurrentUser` dependency
   - Reject unauthenticated requests with 401
   - Inject `CurrentUser` into all route handlers
4. Create `src/helix/api/middleware/audit.py` — Auto-log middleware:
   - Log all state-changing requests (POST, PUT, PATCH, DELETE) to `audit_events` table
   - Include `user_id`, `org_id`, `event_type`, `resource_type`, `payload`, `ip_address`
5. Register all middleware in `main.py`, update all route handlers to accept `CurrentUser` dependency
6. Write auth tests: JWT roundtrip, expired token rejection, org mismatch rejection, middleware 401 on missing token

### Test Gate
```bash
uv run pytest tests/test_auth/ -v --tb=short
```

---

## Phase 9: LLM Gateway — Real API Calls
**Goal:** Actual Claude/OpenAI API calls with streaming, fallback, and metering.
**Complexity:** L

### Tasks
1. Implement `src/helix/llm/gateway.py` — Real async LLM router:
   - `async def call_llm(request: LLMRequest) -> LLMResponse` using `anthropic.AsyncAnthropic`
   - Streaming support via `httpx` SSE
   - Model selection from `LLMPolicy` per org (read from DB)
   - Circuit breaker integration (existing `CircuitBreaker` class)
   - Transparent fallback with audit event emission
2. Create `src/helix/llm/metering.py`:
   - `async def record_usage(session, tracker: TokenUsageTracker)` → persist to `token_usage_events` table
   - Cost calculation using existing `calculate_cost()` function
   - Batch writes via Redis buffer (flush every 500ms)
3. Implement 3-layer compaction with real storage:
   - Micro-compaction: upload to S3/MinIO via `boto3`, replace with reference pointer
   - Auto-compaction: call Haiku to produce structured summary at 83.5% threshold
   - Cross-session: load `workflow_compaction_snapshots` on workflow resume
4. Create `src/helix/llm/structured.py` — PydanticAI structured output wrapper:
   - `async def structured_call(model, output_type: Type[T], prompt) -> T` using PydanticAI
   - Used by Dream Cycle gather phase, lead scoring, classification tasks
5. Write LLM tests: mock Anthropic client, verify fallback cascade, metering persistence, compaction trigger

### Test Gate
```bash
uv run pytest tests/test_llm/ -v --tb=short
```

---

## Phase 10: LangGraph Orchestration — Wire the Graph
**Goal:** Real LangGraph StateGraph, worker agents, DB-backed IPC, Redis pub/sub.
**Complexity:** L

### Tasks
1. Wire `src/helix/orchestration/coordinator.py` — Real LangGraph StateGraph:
   - `create_workflow_graph() -> CompiledGraph` with `StateGraph(WorkflowState)`
   - `add_node()` for plan, execute, approval, verify, failure nodes
   - `add_conditional_edges()` with `should_request_approval` router
   - `graph.compile(checkpointer=PostgresSaver)` for persistence
2. Create `src/helix/orchestration/workers.py` — Worker agent factory:
   - `create_worker_agent(role, tools, model_id) -> CompiledGraph` using `langgraph.prebuilt.create_react_agent`
   - Tool injection per worker role (researcher gets read tools, implementer gets write tools)
   - Hierarchy depth enforcement at spawn time
3. Implement DB-backed IPC:
   - `async def send_message(session, msg: AgentMessage)` → INSERT into `agent_messages` + Redis PUBLISH
   - `async def receive_messages(session, agent_id) -> list[AgentMessage]` → SELECT + mark delivered
   - Redis pub/sub subscriber for real-time notification
4. Implement speculation with real DB savepoints:
   - `async with session.begin_nested() as savepoint:` for speculative execution
   - `savepoint.commit()` on approval, `savepoint.rollback()` on rejection
   - Queue write tool calls during speculation, execute on confirmation
5. Create `src/helix/workers/workflow_tasks.py` — Celery task:
   - `execute_workflow.delay(workflow_id)` dispatches to LangGraph
   - Status polling + WebSocket push on state transitions
6. Write orchestration integration tests: workflow lifecycle through graph, message IPC, savepoint apply/rollback

### Test Gate
```bash
uv run pytest tests/test_orchestration/ -v --tb=short
```

---

## Phase 11: Memory System — Real Vector Search & Dream Cycle
**Goal:** Embedding generation, pgvector queries, Celery dream tasks.
**Complexity:** L

### Tasks
1. Create `src/helix/memory/embeddings.py`:
   - `async def embed_text(text: str, model: str = "text-embedding-3-large") -> list[float]` using OpenAI async client
   - `async def embed_batch(texts: list[str]) -> list[list[float]]` with batching (max 2048 per call)
   - Fallback: Claude Haiku embedding if OpenAI unavailable
2. Implement real vector search in `store.py`:
   - `async def retrieve_relevant(session, org_id, query, limit=10) -> list[MemoryQueryResult]`
   - Raw SQL: `SELECT *, 1 - (embedding <=> $query_vec) AS similarity FROM memory_records WHERE org_id = $org_id AND valid_until IS NULL ORDER BY embedding <=> $query_vec LIMIT $limit`
   - Access control filter: `AND (access_level = 'PUBLIC' OR allowed_roles && $user_roles)`
3. Wire Dream Cycle to real DB + LLM:
   - Orient: `SELECT topic, content FROM memory_records WHERE org_id = :org_id AND valid_until IS NULL`
   - Gather: Call Haiku to extract signals from session JSONL transcripts
   - Consolidate: Call Sonnet to merge/deduplicate, then `embed_text()` + INSERT
   - Prune: DELETE beyond `max_memory_records`, UPDATE `dream_runs` log
4. Create `src/helix/workers/celery_app.py` — Celery configuration:
   - Two queues: `workflow` (high priority) and `dream` (low priority, separate pool)
   - Redis broker from `REDIS_URL`
   - Beat schedule: check dream triggers every 15 minutes
5. Create `src/helix/workers/dream_tasks.py`:
   - `check_dream_triggers()` — iterate orgs, check 3-gate trigger per org
   - `run_dream_cycle_task.delay(org_id)` — acquire Redis SETNX lock, run 4 phases, release
   - Separate Celery queue so dream never blocks workflow execution
6. Write memory integration tests: embed + store + retrieve roundtrip, dream cycle with real DB

### Test Gate
```bash
uv run pytest tests/test_memory/ -v --tb=short
```

---

## Phase 12: Integration Bus — Enterprise Tool Expansion
**Goal:** Generic tool registry, Composio adapter, 10 enterprise integrations.
**Complexity:** L

### Tasks
1. Create `src/helix/integrations/registry.py` — Dynamic tool registry:
   - `ToolRegistry` class that loads tool definitions per `(org_id, integration_id)` from DB
   - Alphabetical sort for prompt cache optimization (from Claude Code)
   - Tool schema generation for LLM system prompt injection
   - Runtime risk classification override per tenant
2. Create `src/helix/integrations/composio.py` — Composio SDK adapter:
   - `async def get_tools(integration_id) -> list[IntegrationTool]` — fetch available actions from Composio
   - `async def execute_tool(tool_name, arguments, connection_id) -> dict` — execute via Composio
   - OAuth flow initiation + callback handling for new integrations
   - Per-integration rate limiting via Redis token bucket
3. Create `src/helix/integrations/webhooks.py` — Inbound event handler:
   - FastAPI endpoint: `POST /api/v1/webhooks/{integration_id}`
   - Verify webhook signatures per provider
   - Route events to workflow triggers: Jira issue updated → start workflow
   - Event queue via Redis for async processing
4. Build tool definitions for top 10 enterprise integrations:

   | Integration | Category | Key Tools | Risk Levels |
   |---|---|---|---|
   | **Slack** | Communication | send_message, list_channels, search_messages, create_channel | LOW-MEDIUM |
   | **Jira** | Project Mgmt | create_issue, update_issue, get_issue, transition_issue, add_comment | LOW-HIGH |
   | **Google Workspace** | Productivity | send_email, create_doc, create_event, list_files, share_file | LOW-HIGH |
   | **Microsoft 365** | Productivity | send_email, create_event, list_files, search_email | LOW-HIGH |
   | **HubSpot** | CRM | create_contact, update_deal, list_deals, create_task, send_sequence | LOW-HIGH |
   | **ServiceNow** | ITSM | create_incident, update_incident, get_incident, assign_incident | LOW-HIGH |
   | **Zendesk** | Helpdesk | create_ticket, update_ticket, add_comment, assign_ticket | LOW-HIGH |
   | **GitHub** | DevOps | create_issue, create_pr, list_prs, add_comment, merge_pr | LOW-CRITICAL |
   | **Notion** | Knowledge | create_page, update_page, search, add_to_database | LOW-MEDIUM |
   | **DocuSign** | eSign | send_envelope, get_status, void_envelope | MEDIUM-CRITICAL |

5. Create `src/helix/integrations/skills.py` — Agent skill definitions:

   | Skill | What It Does | Tools Used |
   |---|---|---|
   | `summarize_thread` | Summarize a Slack thread or email chain | Slack/Gmail read + LLM |
   | `draft_email` | Draft contextual email from memory + CRM data | CRM read + LLM + Gmail |
   | `score_lead` | Score inbound lead using firmographic + behavioral data | CRM + enrichment + LLM |
   | `create_report` | Generate weekly/monthly report from multiple sources | Multiple reads + LLM + Docs |
   | `route_ticket` | Classify and route support ticket to correct team | Zendesk/ServiceNow + LLM |
   | `schedule_meeting` | Find availability and schedule across calendars | Google Calendar + Slack + LLM |
   | `onboard_user` | Multi-system user provisioning workflow | HR + Slack + Jira + GitHub |
   | `detect_churn_risk` | Monitor usage + sentiment for at-risk accounts | CRM + Zendesk + LLM |
   | `process_invoice` | Extract, match, approve, and post invoices | Email + ERP + LLM + approval gate |
   | `incident_response` | Alert → ticket → notify → escalate → postmortem | PagerDuty + ServiceNow + Slack + Docs |

6. Write integration tests: Composio mock, tool execution flow, webhook signature verification, rate limiting

### Test Gate
```bash
uv run pytest tests/test_integrations/ -v --tb=short
```

---

## Phase 13: API Completion & Real-Time
**Goal:** All remaining routes, WebSocket, complete API surface.
**Complexity:** M

### Tasks
1. Complete stub routes with real DB queries:
   - `orgs.py`: real INSERT/SELECT via SQLAlchemy session
   - `workflows.py`: create → dispatch to Celery, get → SELECT with status, list → paginated query
   - `memory.py`: create → embed + INSERT, search → vector query, dream trigger → Celery dispatch
   - `approvals.py`: decide → process_decision + resolve_speculation + audit event
2. Create missing routes:
   - `src/helix/api/routes/agents.py` — list agents per workflow, get agent trace/messages
   - `src/helix/api/routes/integrations.py` — add/remove integrations, OAuth flow, list tools per integration
   - `src/helix/api/routes/audit.py` — query audit trail with pagination, integrity verification endpoint (chain hash check)
3. Create WebSocket endpoint `src/helix/api/routes/ws.py`:
   - `ws://host/api/v1/ws` — authenticated WebSocket connection
   - Push approval requests to connected users in real-time
   - Push workflow status transitions
   - Redis pub/sub subscriber per connection
4. Add pagination to all list endpoints:
   - `limit` + `offset` query params with `X-Total-Count` header
   - Default limit 50, max 200
5. Write API integration tests: full CRUD flows, WebSocket connection, pagination

### Test Gate
```bash
uv run pytest tests/test_api/ -v --tb=short && uv run ruff check src/ && uv run mypy src/
```

---

## Phase 14: Hardening & Deployment (Original Phase 6)
**Goal:** Docker, Helm, observability, load testing.
**Complexity:** M

### Tasks
1. Verify `Dockerfile` (multi-stage) and `docker-compose.yml` with healthchecks — add Celery worker and beat services
2. Create Helm chart `deploy/helm/helix/`:
   - API deployment (2+ replicas)
   - Celery workflow workers (autoscaling)
   - Celery dream workers (separate pool, low priority)
   - Celery beat (single instance)
   - ConfigMaps + Secrets for env vars
   - Ingress with TLS
3. Wire OpenTelemetry:
   - Traces on all LLM calls (model, tokens, latency, fallback)
   - Spans on workflow phases (plan → execute → approve → verify)
   - Metrics: token usage per org, approval latency p50/p95, dream cycle duration
4. Wire Sentry with structlog integration for error tracking
5. Create `scripts/load_test.py` — k6 or Locust:
   - Concurrent workflow creation (target: 100 concurrent)
   - Approval flow under load
   - Memory semantic search latency (target: <50ms p95)
   - Dream cycle with 1000+ memory records
6. Security audit: no hardcoded secrets, no SQL injection vectors, prompt injection defense on all tool outputs

### Test Gate
```bash
docker compose up -d && docker compose exec api uv run pytest tests/ -v --tb=short && docker compose down
```

---

## Phase Summary (v2)

| Phase | Name | Tasks | Complexity | Key Deliverable |
|---|---|---|---|---|
| 7 | Database Foundation | 5 | M | Alembic, RLS, pgvector, tenant middleware |
| 8 | Auth & Security | 6 | M | JWT signing, WorkOS SSO, auth middleware, audit logging |
| 9 | LLM Gateway I/O | 5 | L | Real Claude/OpenAI calls, streaming, metering, compaction |
| 10 | Orchestration Wiring | 6 | L | LangGraph StateGraph, worker agents, DB IPC, savepoints |
| 11 | Memory I/O | 6 | L | Embeddings, pgvector search, Celery dream tasks |
| 12 | Integration Expansion | 6 | L | Composio adapter, 10 integrations, 10 agent skills, webhooks |
| 13 | API Completion | 5 | M | Real CRUD routes, WebSocket, pagination |
| 14 | Hardening | 6 | M | Docker, Helm, OpenTelemetry, Sentry, load tests |

**Critical path:** Phase 7 → Phase 8 → (Phase 9 + Phase 10 + Phase 11 in parallel) → Phase 12 → Phase 13 → Phase 14

Phases 9, 10, and 11 can run in parallel — LLM calls, orchestration wiring, and memory I/O are independent until integration in Phase 12.

---

## Multi-Tool Workflow Templates (Post Phase 12)

These are the first workflow templates to build once the integration bus is wired:

| # | Workflow | Systems | Trigger | Approval Gates |
|---|---|---|---|---|
| 1 | **Lead-to-Opportunity** | Apollo → Salesforce → Outreach → Slack | New inbound lead | Opp creation (MEDIUM) |
| 2 | **Employee Onboarding** | Greenhouse → Workday → Slack → GitHub → Jira → Asana | Offer accepted webhook | Provisioning (HIGH) |
| 3 | **Incident Response** | PagerDuty → ServiceNow → Slack → Google Docs | Alert webhook | Escalation (HIGH) |
| 4 | **Customer Health Alert** | Gainsight → Zendesk → Asana → Calendly | Score drop event | QBR scheduling (LOW) |
| 5 | **Invoice Processing** | Gmail → NetSuite → Slack → ERP | Email inbound | Payment approval (CRITICAL) |
| 6 | **Deal Desk** | Salesforce → Google Sheets → Slack → DocuSign | Deal stage change | Pricing approval (HIGH) |
| 7 | **Weekly Pipeline Report** | Salesforce → Google Docs → Slack | Cron (Monday 8am) | None (auto-deliver) |
| 8 | **Support Escalation** | Zendesk → Slack → Jira → CRM | SLA breach event | Assignment (MEDIUM) |
