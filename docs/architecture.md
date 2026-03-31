# Architecture: Helix Enterprise AI Agent Orchestration Platform

## System Overview

Helix is a multi-tenant enterprise platform providing AI agent orchestration and institutional memory. It exposes a FastAPI control plane, a LangGraph-powered orchestration engine, a PostgreSQL+pgvector memory substrate, and an integration bus for SaaS connectors — all governed by RBAC, audit trails, and per-tenant isolation boundaries.

The architecture is directly informed by the Claude Code (Tengu) production system leaked March 2026. Each major subsystem maps to a Claude Code component, with enterprise adaptations: multi-tenancy replaces per-user scoping, database-backed state replaces file-based IPC, transparent policies replace silent fallbacks, and OS-level isolation replaces userspace workarounds.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          NEXUS PLATFORM BOUNDARY                            │
│                                                                             │
│  ┌──────────────┐    ┌──────────────────────────────────────────────────┐  │
│  │   WorkOS     │    │                  CONTROL PLANE                   │  │
│  │  SSO / SCIM  │◄──►│   FastAPI  ·  Auth Middleware  ·  RBAC Engine   │  │
│  └──────────────┘    │        Tenant Router  ·  Audit Logger           │  │
│                      └────────────────────┬─────────────────────────────┘  │
│                                           │                                │
│          ┌────────────────────────────────▼──────────────────────────────┐ │
│          │                   ORCHESTRATION ENGINE                        │ │
│          │  LangGraph State Machine  ·  Agent Lifecycle Manager          │ │
│          │  Plan/Approval FSM  ·  Human-in-the-Loop Escalation Chain     │ │
│          │  Coordinator Agent  ──spawns──►  Worker Pool (N agents)       │ │
│          └──────┬─────────────────────────────────────────┬─────────────┘ │
│                 │                                         │               │
│  ┌──────────────▼──────────────┐    ┌────────────────────▼─────────────┐ │
│  │        LLM GATEWAY          │    │       INTEGRATION BUS             │ │
│  │  Multi-provider router      │    │  Composio/Nango connector layer   │ │
│  │  Model fallback policies    │    │  Salesforce · Jira · Slack · SAP  │ │
│  │  Token metering + billing   │    │  Risk classification per tool     │ │
│  │  Context compaction engine  │    │  Approval workflows + webhooks    │ │
│  └──────────────┬──────────────┘    └────────────────────┬─────────────┘ │
│                 │                                         │               │
│  ┌──────────────▼─────────────────────────────────────────▼─────────────┐ │
│  │                     MEMORY & STATE SUBSTRATE                          │ │
│  │  PostgreSQL 16  ·  pgvector  ·  Redis                                 │ │
│  │  Org-scoped memory  ·  Workflow state  ·  Audit trail                 │ │
│  │  Embedding store  ·  Task queues  ·  Pub/sub                          │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌────────────────────────┐    ┌─────────────────────────────────────────┐ │
│  │  PREDICTIVE WORKFLOW   │    │        BACKGROUND SERVICES              │ │
│  │  ENGINE                │    │  Memory Consolidation (Dream Cycle)     │ │
│  │  Speculative pre-comp  │    │  Celery/ARQ workers  ·  Metrics         │ │
│  │  DB-transaction sandbox│    │  Audit archival  ·  Token accounting    │ │
│  └────────────────────────┘    └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Orchestration Engine
**Claude Code reference:** Coordinator Mode (`CLAUDE_CODE_COORDINATOR_MODE=1`) with TeammateTool (13 operations), git worktree isolation per agent, file-based IPC with lock files, one-level subagent hierarchy, and explicit parallelism over chaining in worker prompts.

**What we do differently:**
- Multi-tenant isolation: every agent execution is scoped to `(org_id, workflow_id)`. Agents from different tenants can never share state.
- RBAC per operation: TeammateTool's 13 operations map to fine-grained permissions. A read-only role can observe agent state but cannot `spawnTeam`, `approvePlan`, or `broadcast`.
- Database-backed IPC: agent messages stored in `agent_messages` table (PostgreSQL) instead of `~/.claude/teams/`. Redis pub/sub delivers real-time notifications. No file lock contention across distributed workers.
- Configurable hierarchy depth: Claude Code hard-codes one level (subagents cannot spawn sub-subagents). Helix allows configurable depth (default: 2) per workflow template, enforced in the state machine.
- Human-in-the-loop as first-class FSM state: approval is not a side-channel — it is a named state (`AWAITING_APPROVAL`) in the LangGraph workflow with timeout, escalation, and SLA tracking.
- Enterprise SaaS event bus: coordinator can subscribe to external events (Jira ticket created, Salesforce opportunity updated) as workflow triggers, not just user prompts.

**Technology:** LangGraph 0.3+ for state machine definition. Each workflow is a `StateGraph` with typed state (`WorkflowState`, a Pydantic model). Agent workers are `langgraph.prebuilt.create_react_agent` instances with injected tool sets.

**Inputs:** `WorkflowCreateRequest` (tenant_id, workflow_template_id, initial_context, trigger_source)
**Outputs:** `WorkflowResult` (final_state, artifacts, agent_trace, token_usage, audit_events)

**Key interfaces:**
```python
class WorkflowState(BaseModel):
    workflow_id: UUID
    org_id: UUID
    phase: Literal["PLANNING","EXECUTING","AWAITING_APPROVAL","VERIFYING","COMPLETE","FAILED"]
    coordinator_agent_id: UUID
    worker_agent_ids: list[UUID]
    messages: list[AgentMessage]
    pending_approval: ApprovalRequest | None
    speculation_cache: dict[str, SpeculativeResult]
    token_usage: TokenUsage
    created_at: datetime
    updated_at: datetime
```

**Database tables:**
```sql
-- Workflow instances
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    template_id UUID REFERENCES workflow_templates(id),
    status VARCHAR(32) NOT NULL,         -- FSM phase
    coordinator_agent_id UUID,
    initial_context JSONB,
    result JSONB,
    token_usage JSONB,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Agent instances within workflows
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    org_id UUID NOT NULL REFERENCES orgs(id),
    role VARCHAR(64) NOT NULL,           -- coordinator | researcher | implementer | verifier
    model_id VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    spawned_by UUID REFERENCES agents(id),
    hierarchy_depth SMALLINT DEFAULT 0,
    token_usage JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    terminated_at TIMESTAMPTZ
);

-- IPC message bus (replaces file-based ~/.claude/teams/)
CREATE TABLE agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    org_id UUID NOT NULL REFERENCES orgs(id),
    sender_agent_id UUID NOT NULL REFERENCES agents(id),
    recipient_agent_id UUID REFERENCES agents(id),  -- NULL = broadcast
    message_type VARCHAR(64) NOT NULL,               -- write | broadcast | approvePlan | etc.
    payload JSONB NOT NULL,
    delivered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_agent_messages_workflow ON agent_messages(workflow_id, created_at);

-- Approval requests (HITL)
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    org_id UUID NOT NULL REFERENCES orgs(id),
    requested_by_agent_id UUID NOT NULL REFERENCES agents(id),
    action_description TEXT NOT NULL,
    risk_level VARCHAR(16) NOT NULL,     -- LOW | MEDIUM | HIGH | CRITICAL
    integration_id UUID REFERENCES integrations(id),
    payload JSONB NOT NULL,
    status VARCHAR(32) DEFAULT 'PENDING',
    decided_by UUID REFERENCES users(id),
    decision_reason TEXT,
    sla_deadline TIMESTAMPTZ,
    escalated_to UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    decided_at TIMESTAMPTZ
);
```

---

### 2. Memory System (Dream Cycle)
**Claude Code reference:** autoDream — 4-phase consolidation (Orient → Gather → Consolidate → Prune), 3-gate trigger (24hr + 5 sessions + lock), forked read-only subagent, 200-line/25KB MEMORY.md cap, YAML frontmatter files, Sonnet-powered relevance selector retrieving up to 5 files per turn.

**What we do differently:**
- Organization-scoped memory: memory is owned by `org_id`, not a single user. All agents in an org can read org-level memory; users can have personal memory isolated within the org.
- PostgreSQL + pgvector: no file-based YAML. Memories are rows with embedding vectors. The relevance selector runs a vector similarity query (`<=>` cosine distance) instead of keyword grep, returning top-K by semantic relevance.
- Semantic retrieval: autoDream's Sonnet-powered selector reads 5 files sequentially. Helix runs `SELECT ... ORDER BY embedding <=> $query_vec LIMIT 10` — one DB round-trip instead of N file reads. Latency: ~5ms vs ~200ms.
- Memory access controls: per-role permissions on memory topics. A `viewer` role agent can read public memory but not write. `CONFIDENTIAL`-tagged memories are isolated to specific roles.
- Cross-agent sharing with isolation: coordinator can designate memory as `SHARED` (all agents in workflow can read) or `ISOLATED` (agent-private). Prevents information leakage between parallel workers.
- Configurable consolidation triggers: `DreamConfig` per org overrides the global 24hr/5-session defaults. High-activity orgs can set 1hr/1-session; low-activity orgs can set 72hr/10-session.
- Memory versioning: every write appends a new version row. No in-place updates. Full history queryable for audit. Automated pruning keeps only the last N versions per topic.
- GDPR compliance: memory gather phase in autoDream reads raw session transcripts. Helix never stores PII in memory rows without explicit user consent flag; the consolidation worker applies a PII-stripping pass before embedding.

**Technology:** Celery worker for consolidation cycle. `text-embedding-3-large` (OpenAI) or `claude-3-haiku` for embeddings. pgvector for similarity search.

**Inputs:** Session transcripts (JSONL in S3/local), org memory store
**Outputs:** Updated memory rows with embeddings, updated memory index

**Key interfaces:**
```python
class MemoryRecord(BaseModel):
    id: UUID
    org_id: UUID
    agent_id: UUID | None       # None = org-level
    topic: str
    content: str
    tags: list[str]
    access_level: Literal["PUBLIC", "ROLE_RESTRICTED", "CONFIDENTIAL"]
    allowed_roles: list[str]
    source_session_ids: list[UUID]
    embedding: list[float]      # 1536-dim, stored in pgvector column
    version: int
    valid_from: datetime
    valid_until: datetime | None
    created_at: datetime

class DreamConfig(BaseModel):
    org_id: UUID
    min_hours_between_runs: int = 24
    min_sessions_between_runs: int = 5
    max_memory_records: int = 500
    max_bytes_per_record: int = 8192
    pii_strip_enabled: bool = True
    consolidation_model: str = "claude-sonnet-4-6"
```

**Database tables:**
```sql
CREATE TABLE memory_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    user_id UUID REFERENCES users(id),      -- NULL = org-level memory
    agent_id UUID REFERENCES agents(id),    -- originating agent
    topic VARCHAR(256) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    access_level VARCHAR(32) DEFAULT 'PUBLIC',
    allowed_roles TEXT[] DEFAULT '{}',
    source_session_ids UUID[] DEFAULT '{}',
    embedding vector(1536),                  -- pgvector column
    version INTEGER NOT NULL DEFAULT 1,
    valid_from TIMESTAMPTZ DEFAULT now(),
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
-- Approximate nearest neighbor index for semantic retrieval
CREATE INDEX idx_memory_embedding ON memory_records
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memory_org_topic ON memory_records(org_id, topic);
CREATE INDEX idx_memory_valid ON memory_records(org_id, valid_until)
    WHERE valid_until IS NULL;

CREATE TABLE dream_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    triggered_by VARCHAR(64),              -- schedule | manual | api
    phase VARCHAR(32) NOT NULL,            -- ORIENT | GATHER | CONSOLIDATE | PRUNE | COMPLETE | FAILED
    sessions_processed INTEGER,
    records_created INTEGER,
    records_updated INTEGER,
    records_pruned INTEGER,
    tokens_used INTEGER,
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

---

### 3. LLM Gateway
**Claude Code reference:** 46K-line QueryEngine with `while(true)` retry loop, 3 silent model downgrades (529 → Opus→Sonnet, streaming hang → non-streaming fallback, rate limit → exponential backoff), 3-layer context compaction (micro at tool output, auto at 83.5%, manual), circuit breaker at 3 failures, system prompt split at `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` into static (cacheable) and dynamic sections.

**What we do differently:**
- Multi-provider: Anthropic (primary), OpenAI (fallback), Azure OpenAI (enterprise on-prem option), Bedrock (AWS customers). Provider selected per tenant via `LLMPolicy`.
- Per-tenant rate limiting and cost tracking: Redis token bucket per `(org_id, model_tier)`. Every API call writes token usage to `token_usage_events` for billing attribution.
- Transparent fallback: Claude Code silently downgrades models. Helix emits `model_fallback` audit events with reason. Tenants can configure `allow_silent_downgrade: false` to surface degradation to users.
- Configurable fallback policy: `ModelFallbackPolicy` per org defines the cascade chain. Default: `claude-opus-4-6 → claude-sonnet-4-6 → claude-haiku-4-5`. Custom chains allowed.
- Long-running compaction: autoDream consolidates within hours. Enterprise workflows run for days. Helix compaction persists intermediate summaries to `workflow_compaction_snapshots` so interrupted workflows resume without losing context.
- Token accounting and billing: every LLM call tagged with `workflow_id`, `agent_id`, `org_id`, and `cost_center`. Aggregated in `token_usage_events`. Billing service reads daily aggregates.
- System prompt cache optimization: inherits Claude Code's `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` pattern. Static sections (tool definitions, org-level instructions, integration schemas) are separated from dynamic sections (user identity, workflow state, session context). Static sections are sorted alphabetically to maximize cache hit rate (same insight as Claude Code's alphabetical tool sort).

**Technology:** PydanticAI for structured LLM outputs. `httpx` with async streaming. Redis for rate limit state and response caching.

**Inputs:** `LLMRequest` (messages, model, tools, org_id, workflow_id, agent_id)
**Outputs:** `LLMResponse` (content, tool_calls, token_usage, model_used, fallback_occurred, compaction_applied)

**Compaction layers (adapted from Claude Code):**
1. **Micro-compaction:** Tool outputs > 8KB are offloaded to S3. Agent receives a reference pointer. Threshold configurable per org.
2. **Auto-compaction:** Fires at 83.5% context usage (matching Claude Code's ratio). Produces structured summary: intent, decisions, integration actions taken, open approvals, next steps. Summary appended to `workflow_compaction_snapshots`.
3. **Cross-session compaction:** Unique to Helix. When a workflow resumes after interruption, compaction snapshot is injected as the initial context frame.

**Database tables:**
```sql
CREATE TABLE token_usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    workflow_id UUID REFERENCES workflows(id),
    agent_id UUID REFERENCES agents(id),
    user_id UUID REFERENCES users(id),
    model_id VARCHAR(128) NOT NULL,
    provider VARCHAR(64) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER DEFAULT 0,
    cache_write_tokens INTEGER DEFAULT 0,
    cost_usd NUMERIC(12,8),
    cost_center VARCHAR(128),
    fallback_occurred BOOLEAN DEFAULT FALSE,
    fallback_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_token_usage_org_date ON token_usage_events(org_id, created_at);

CREATE TABLE workflow_compaction_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    context_pct_at_trigger NUMERIC(5,2),
    tokens_before INTEGER,
    tokens_after INTEGER,
    summary JSONB NOT NULL,      -- intent, decisions, artifacts, pending, next_steps
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE llm_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id) UNIQUE,
    primary_model VARCHAR(128) DEFAULT 'claude-sonnet-4-6',
    fallback_chain JSONB DEFAULT '["claude-haiku-4-5"]',
    allow_silent_downgrade BOOLEAN DEFAULT TRUE,
    max_context_tokens INTEGER DEFAULT 200000,
    compaction_threshold_pct NUMERIC(5,2) DEFAULT 83.5,
    provider_preference VARCHAR(64) DEFAULT 'anthropic',
    azure_endpoint TEXT,
    bedrock_region VARCHAR(64),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

---

### 4. Integration Bus
**Claude Code reference:** 40-60 tools with LOW/MEDIUM/HIGH risk classification. `classifyYoloAction()` uses Claude inference for auto-approval. Protected files unconditionally blocked. Concurrent reads, serial writes. Hooks system: event → matcher → hook pipeline with `command`, `prompt`, `HTTP`, `agent` hook types.

**What we do differently:**
- Tools are SaaS integrations via Composio or Nango. Each integration (Salesforce, Jira, Slack, SAP, GitHub, etc.) is modeled as a set of tools with individual risk ratings.
- Risk classification per integration per tenant: a `read_opportunity` action in Salesforce may be LOW for all tenants, but `delete_account` is CRITICAL and requires multi-party approval regardless of tenant policy.
- Approval workflows with escalation: Claude Code's model is binary (approve/deny). Helix has an `ApprovalPolicy` tree: auto-approve LOW, require requester's manager for MEDIUM, require CISO + legal for CRITICAL, with SLA timers that escalate if no decision is made.
- Webhook-driven events: integrations emit inbound events (Jira issue updated, Salesforce deal closed) that trigger workflows. The hook pipeline is inverted: external event → Helix → agent, not just agent → external system.
- Rate limiting per integration per tenant: each integration has its own token bucket in Redis keyed by `(org_id, integration_id)`. Prevents one workflow from exhausting a tenant's Salesforce API quota.
- Tool registry alphabetical sort: inherited directly from Claude Code for prompt cache optimization. Integration tools sorted alphabetically in system prompt.

**Technology:** Composio SDK for managed connectors. Nango as fallback for custom OAuth. FastAPI webhook endpoints for inbound events. Redis for per-integration rate limit state.

**Inputs:** `ToolCallRequest` (tool_name, arguments, workflow_id, agent_id, org_id)
**Outputs:** `ToolCallResult` (output, risk_level, approval_required, approval_id, rate_limit_remaining)

**Key interfaces:**
```python
class Integration(BaseModel):
    id: UUID
    org_id: UUID
    provider: str                   # salesforce | jira | slack | sap | github | ...
    connector_type: Literal["composio", "nango", "custom"]
    credential_ref: str             # pointer to secrets manager, never stored inline
    tools: list[IntegrationTool]
    enabled: bool
    rate_limit_per_hour: int

class IntegrationTool(BaseModel):
    name: str
    description: str
    parameters_schema: dict         # JSON Schema
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    requires_approval: bool
    approval_policy_id: UUID | None
    parallel_safe: bool             # concurrent execution allowed
    idempotent: bool

class ApprovalPolicy(BaseModel):
    id: UUID
    org_id: UUID
    name: str
    risk_levels_requiring_approval: list[str]
    approver_roles: list[str]
    escalation_sla_minutes: int
    escalation_target_roles: list[str]
    multi_party_required: bool
    min_approver_count: int = 1
```

**Database tables:**
```sql
CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    provider VARCHAR(64) NOT NULL,
    connector_type VARCHAR(32) NOT NULL,
    credential_ref VARCHAR(512),         -- Vault path or secrets manager ARN
    config JSONB DEFAULT '{}',
    enabled BOOLEAN DEFAULT TRUE,
    rate_limit_per_hour INTEGER DEFAULT 1000,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, provider)
);

CREATE TABLE integration_tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    agent_id UUID NOT NULL REFERENCES agents(id),
    org_id UUID NOT NULL REFERENCES orgs(id),
    integration_id UUID NOT NULL REFERENCES integrations(id),
    tool_name VARCHAR(128) NOT NULL,
    arguments JSONB,
    result JSONB,
    risk_level VARCHAR(16) NOT NULL,
    approval_id UUID REFERENCES approval_requests(id),
    duration_ms INTEGER,
    error TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

### 5. Predictive Workflow Engine
**Claude Code reference:** Speculative execution — background fork pre-executes predicted next prompt. Overlay filesystem sandbox (`~/.claude/speculation/<pid>/`). 20 tool-turn limit, 100 message limit. Freely speculates on reads, blocks writes outside working dir. Pipelining stays multiple steps ahead.

**What we do differently:**
- Speculative workflow pre-computation: when a workflow enters `AWAITING_APPROVAL`, Helix speculatively pre-computes the most likely next phase (assuming approval). On approval, execution is instant because the work is already done. On rejection, the speculative state is discarded.
- Database transaction sandbox: Claude Code uses an overlay filesystem. Helix uses PostgreSQL savepoints. Speculative writes are issued within a `SAVEPOINT speculation_<id>`. On approval: `RELEASE SAVEPOINT`. On rejection: `ROLLBACK TO SAVEPOINT`. No filesystem complexity, no distributed lock issues.
- Configurable depth: Claude Code speculates one step ahead. Helix allows configurable `speculation_depth` (default: 2) per workflow template. High-latency approval workflows can speculate 3-4 steps ahead.
- Read-only integration calls during speculation: same principle as Claude Code. During speculative execution, read-only integration tools (GET requests, queries) are allowed. Write operations (mutations, POSTs) are queued and executed only on confirmation.
- Speculation scoring: each speculative branch is scored by `P(approval) × time_saved`. Low-probability speculations are not pre-computed to avoid wasted LLM calls.

**Technology:** Celery beat for async pre-computation. PostgreSQL savepoints for transaction sandboxing. Redis pub/sub to notify the main workflow when a speculative result is ready.

**Inputs:** Pending `ApprovalRequest` with workflow state snapshot
**Outputs:** Pre-computed `SpeculativeResult` stored in `speculation_cache` (workflow state column) or `speculative_executions` table

**Database tables:**
```sql
CREATE TABLE speculative_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    org_id UUID NOT NULL REFERENCES orgs(id),
    approval_request_id UUID NOT NULL REFERENCES approval_requests(id),
    assumed_decision VARCHAR(16) NOT NULL,  -- APPROVED | REJECTED
    speculation_depth SMALLINT DEFAULT 1,
    pre_computed_state JSONB,
    queued_writes JSONB DEFAULT '[]',       -- write ops blocked until confirmed
    confidence_score NUMERIC(5,4),
    token_cost INTEGER,
    status VARCHAR(32) DEFAULT 'PENDING',   -- PENDING | READY | APPLIED | DISCARDED
    created_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ
);
```

---

## Data Flow Sequences

### Flow 1: Agent Executing a Multi-Step Workflow with Human Approval

```
Client                 API             Orchestration      LLM Gateway    Integration Bus
  │                     │                   │                  │                │
  │  POST /workflows     │                  │                  │                │
  │─────────────────────►│                  │                  │                │
  │                     │  create_workflow()│                  │                │
  │                     │──────────────────►│                  │                │
  │                     │                  │  spawn coordinator│                │
  │                     │                  │──────────────────►│ (planning)     │
  │                     │                  │                  │                │
  │                     │                  │  coordinator → spawn 3 workers    │
  │                     │                  │  [researcher, implementer, verifier]
  │                     │                  │                  │                │
  │                     │                  │  researcher → LLM (Sonnet)        │
  │                     │                  │──────────────────►│                │
  │                     │                  │  tool call: read_opportunity      │
  │                     │                  │──────────────────────────────────►│
  │                     │                  │  result: {opp_data}               │
  │                     │                  │◄──────────────────────────────────│
  │                     │                  │                  │                │
  │                     │                  │  implementer → tool call: update_opportunity
  │                     │                  │  risk_level=HIGH → AWAITING_APPROVAL
  │                     │                  │◄─ approval_request created         │
  │                     │                  │                  │                │
  │  websocket push: approval_request      │                  │                │
  │◄─────────────────────│                 │                  │                │
  │                     │                  │  [SPECULATIVE PRE-COMPUTATION]    │
  │                     │                  │  assume APPROVED → pre-exec next  │
  │                     │                  │  phase in DB savepoint            │
  │                     │                  │                  │                │
  │  POST /approvals/{id}/approve          │                  │                │
  │─────────────────────►│                  │                  │                │
  │                     │  record_decision()│                  │                │
  │                     │──────────────────►│                  │                │
  │                     │                  │  RELEASE SAVEPOINT                │
  │                     │                  │  apply queued writes immediately  │
  │                     │                  │──────────────────────────────────►│
  │                     │                  │  verifier confirms result         │
  │                     │                  │──────────────────►│                │
  │                     │                  │  workflow → COMPLETE               │
  │  GET /workflows/{id} │                  │                  │                │
  │─────────────────────►│                  │                  │                │
  │  {status: COMPLETE, artifacts: [...]}  │                  │                │
  │◄─────────────────────│                 │                  │                │
```

### Flow 2: Memory Consolidation Cycle (Dream Cycle)

```
Celery Scheduler          Dream Worker          DB / pgvector        S3 / Sessions
     │                        │                       │                    │
     │  check_dream_triggers()│                       │                    │
     │  per org every 15min   │                       │                    │
     │─────────────────────── │                       │                    │
     │  org_123: last_run=26hr│                       │                    │
     │          sessions=7    │                       │                    │
     │  → triggers satisfied  │                       │                    │
     │                        │                       │                    │
     │  acquire_dream_lock(org_123) → Redis SETNX     │                    │
     │  lock acquired         │                       │                    │
     │                        │                       │                    │
     │─ dispatch dream_task ──►│                       │                    │
     │                        │                       │                    │
     │                    PHASE 1: ORIENT              │                    │
     │                        │  SELECT topic, content │                    │
     │                        │  FROM memory_records   │                    │
     │                        │  WHERE org_id=123      │                    │
     │                        │──────────────────────►│                    │
     │                        │  existing memory index │                    │
     │                        │◄──────────────────────│                    │
     │                        │                       │                    │
     │                    PHASE 2: GATHER SIGNAL       │                    │
     │                        │  fetch session JSONLs since last_run        │
     │                        │──────────────────────────────────────────►│
     │                        │  session transcripts   │                    │
     │                        │◄──────────────────────────────────────────│
     │                        │  LLM (Haiku): extract corrections,         │
     │                        │  decisions, recurring themes               │
     │                        │                       │                    │
     │                    PHASE 3: CONSOLIDATE         │                    │
     │                        │  LLM (Sonnet): merge,  │                    │
     │                        │  deduplicate, strip PII│                    │
     │                        │  generate embeddings   │                    │
     │                        │──────────────────────►│                    │
     │                        │  INSERT/UPDATE memory_records + vectors     │
     │                        │◄──────────────────────│                    │
     │                        │                       │                    │
     │                    PHASE 4: PRUNE               │                    │
     │                        │  DELETE obsolete rows  │                    │
     │                        │  enforce max_records   │                    │
     │                        │  UPDATE dream_runs     │                    │
     │                        │──────────────────────►│                    │
     │  release_dream_lock(org_123)                    │                    │
     │                        │                       │                    │
```

### Flow 3: New Tenant Onboarding with Integration Setup

```
Admin Client           Control Plane         WorkOS          Secrets Mgr     Composio
     │                      │                   │                 │               │
     │  POST /orgs           │                   │                 │               │
     │  {name, sso_domain,   │                   │                 │               │
     │   plan, scim_token}   │                   │                 │               │
     │──────────────────────►│                   │                 │               │
     │                      │  create_org()      │                 │               │
     │                      │  provision_workos()│                 │               │
     │                      │──────────────────►│                 │               │
     │                      │  {org_id, sso_url} │                 │               │
     │                      │◄──────────────────│                 │               │
     │                      │                   │                 │               │
     │                      │  create default RBAC roles           │               │
     │                      │  (admin, operator, viewer, auditor)  │               │
     │                      │  provision Redis namespaces          │               │
     │                      │  provision pgvector partition        │               │
     │                      │  create DreamConfig (default params) │               │
     │                      │  create LLMPolicy (default models)  │               │
     │                      │                   │                 │               │
     │  201 {org_id, sso_url}│                   │                 │               │
     │◄──────────────────────│                   │                 │               │
     │                      │                   │                 │               │
     │  POST /orgs/{id}/integrations             │                 │               │
     │  {provider: "salesforce", ...}            │                 │               │
     │──────────────────────►│                   │                 │               │
     │                      │  initiate_oauth()  │                 │               │
     │                      │──────────────────────────────────────────────────►│
     │                      │  {auth_url}        │                 │               │
     │◄──────────────────────│                   │                 │               │
     │  [admin completes OAuth in browser]       │                 │               │
     │  Composio webhook: oauth_complete         │                 │               │
     │──────────────────────►│                   │                 │               │
     │                      │  store credential_ref (Vault path)  │               │
     │                      │──────────────────────────────────►│               │
     │                      │  fetch tool schema for salesforce   │               │
     │                      │──────────────────────────────────────────────────►│
     │                      │  {tools: [...], risk_levels: {...}} │               │
     │                      │◄──────────────────────────────────────────────────│
     │                      │  INSERT integrations + tool risk classifications   │
     │                      │  bind default ApprovalPolicy for HIGH/CRITICAL     │
     │  201 {integration_id} │                   │                 │               │
     │◄──────────────────────│                   │                 │               │
```

---

## Database Schema (Complete Key Tables)

```sql
-- Tenant foundation
CREATE TABLE orgs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(256) NOT NULL,
    slug VARCHAR(128) UNIQUE NOT NULL,
    workos_org_id VARCHAR(256) UNIQUE,
    plan VARCHAR(32) DEFAULT 'enterprise',
    status VARCHAR(32) DEFAULT 'active',
    on_prem BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Users (linked to WorkOS identity)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    workos_user_id VARCHAR(256) UNIQUE NOT NULL,
    email VARCHAR(320) NOT NULL,
    display_name VARCHAR(256),
    roles TEXT[] DEFAULT '{}',
    last_active_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- RBAC: role → permission grants
CREATE TABLE role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    role VARCHAR(64) NOT NULL,
    resource VARCHAR(128) NOT NULL,   -- workflow | agent | memory | integration | approval
    action VARCHAR(64) NOT NULL,      -- create | read | update | delete | execute | approve
    conditions JSONB DEFAULT '{}',    -- e.g. {risk_level: ["LOW", "MEDIUM"]}
    UNIQUE(org_id, role, resource, action)
);

-- Immutable audit trail (append-only, no UPDATE/DELETE)
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    user_id UUID REFERENCES users(id),
    agent_id UUID REFERENCES agents(id),
    event_type VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64),
    resource_id UUID,
    payload JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
) PARTITION BY RANGE (created_at);
-- Monthly partitions: audit_events_2026_03, audit_events_2026_04, ...
-- RLS policy: org_id must match authenticated tenant
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_tenant_isolation ON audit_events
    USING (org_id = current_setting('app.current_org_id')::UUID);

-- Workflow templates
CREATE TABLE workflow_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID REFERENCES orgs(id),   -- NULL = platform-level template
    name VARCHAR(256) NOT NULL,
    description TEXT,
    langgraph_definition JSONB NOT NULL,
    max_hierarchy_depth SMALLINT DEFAULT 2,
    speculation_depth SMALLINT DEFAULT 1,
    default_model VARCHAR(128) DEFAULT 'claude-sonnet-4-6',
    is_public BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## External Dependencies

| Service | Purpose | Auth Method | Failure Mode |
|---|---|---|---|
| Anthropic API | Primary LLM | API key (header `x-api-key`) | Fallback to OpenAI; circuit breaker at 3 failures |
| OpenAI API | Fallback LLM + embeddings | API key | Mark provider unavailable; queue requests |
| Azure OpenAI | On-prem enterprise option | Managed Identity or API key | Regional failover |
| WorkOS | SSO, SCIM, Directory Sync | API key + webhook signing secret | Auth failures reject login; no silent bypass |
| Composio | SaaS integration connectors | API key per org | Mark integration unavailable; surface to operator |
| Nango | Custom OAuth connector management | API key | Fallback to manual credential injection |
| HashiCorp Vault | Secrets management | AppRole (k8s: ServiceAccount JWT) | Startup fails fast if Vault unreachable |
| PostgreSQL 16 | Primary data store | DSN with SSL required | Read replicas for read-only queries; failover via pgBouncer |
| Redis 7 | Cache, pub/sub, task queues, rate limits | AUTH password + TLS | Rate limiting degrades to DB queries; pub/sub reconnects |
| S3 / GCS / MinIO | Session transcripts, large tool outputs | IAM role (cloud) / static key (on-prem) | Micro-compaction falls back to inline storage |
| Celery broker | Background task queue | Redis (same instance) | Tasks queued in DB fallback table |

---

## Environment Variables

```bash
# Core
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/helix?ssl=require
REDIS_URL=redis://:password@host:6379/0
SECRET_KEY=                          # 32-byte random, for JWT signing
ENVIRONMENT=production               # development | staging | production

# LLM providers
ANTHROPIC_API_KEY=
OPENAI_API_KEY=                      # fallback provider + embeddings
AZURE_OPENAI_ENDPOINT=               # optional, on-prem enterprise
AZURE_OPENAI_API_KEY=
DEFAULT_EMBEDDING_MODEL=text-embedding-3-large

# Identity
WORKOS_API_KEY=
WORKOS_CLIENT_ID=
WORKOS_WEBHOOK_SECRET=
JWT_ALGORITHM=RS256
JWT_PUBLIC_KEY_PATH=                 # PEM path, or inline for container envs

# Integrations
COMPOSIO_API_KEY=
NANGO_SECRET_KEY=
NANGO_PUBLIC_KEY=

# Secrets management
VAULT_ADDR=https://vault.internal:8200
VAULT_ROLE_ID=                       # AppRole auth
VAULT_SECRET_ID=
# On Kubernetes: VAULT_K8S_ROLE=helix-api (use ServiceAccount JWT instead)

# Storage
S3_BUCKET_SESSIONS=helix-sessions
S3_BUCKET_ARTIFACTS=helix-artifacts
S3_ENDPOINT_URL=                     # Override for MinIO on-prem
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1

# LLM Gateway
DEFAULT_PRIMARY_MODEL=claude-sonnet-4-6
DEFAULT_FALLBACK_MODEL=claude-haiku-4-5
COMPACTION_THRESHOLD_PCT=83.5
MICRO_COMPACTION_THRESHOLD_BYTES=8192
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3

# Memory / Dream Cycle
DREAM_CYCLE_ENABLED=true
DREAM_DEFAULT_MIN_HOURS=24
DREAM_DEFAULT_MIN_SESSIONS=5
DREAM_PII_STRIP_ENABLED=true

# Speculation
SPECULATION_ENABLED=true
SPECULATION_DEFAULT_DEPTH=2

# Observability
LOG_LEVEL=INFO
SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=        # OpenTelemetry collector
```

---

## Security Architecture

### Multi-Tenant Isolation
Three enforcement layers to prevent cross-tenant data access:

1. **Application layer:** Every database query is scoped with `WHERE org_id = :current_org_id`. The `current_org_id` is extracted from the verified JWT on each request and injected as a FastAPI dependency.
2. **Database layer:** PostgreSQL Row Level Security (RLS) policies on all tenant-scoped tables. Even a miscoded query will not return another tenant's rows. RLS is enabled at migration time and cannot be disabled at runtime.
3. **Agent isolation:** Each agent process receives credentials scoped to its `(org_id, workflow_id)`. Agents cannot query memory, integrations, or workflows outside their org. Agent tokens are short-lived JWTs (15-minute TTL) issued by the orchestration engine.

### RBAC Model

Four built-in roles (customizable per org):

| Role | Capabilities |
|---|---|
| `admin` | Full org management, all resources, approve CRITICAL actions |
| `operator` | Create/run workflows, approve HIGH actions, manage integrations |
| `viewer` | Read-only on workflows, agents, memory (PUBLIC access level only) |
| `auditor` | Read-only on audit trail, token usage, cannot view workflow content |

Custom roles are defined in `role_permissions` table. Permission checks use `has_permission(user_id, resource, action, conditions)` which evaluates the role permission tree plus any condition predicates (e.g., risk level constraints).

Agent actions are subject to the same RBAC check as human actions. When an agent calls an integration tool, the check is `has_permission(agent_id, integration_id + tool_name, "execute", {risk_level: tool.risk_level})`.

### Audit Trail

All state-changing operations (workflow create/update/complete, approval decisions, integration tool executions, memory writes, user role changes, tenant config changes) write to `audit_events`. Properties:
- Table is append-only. `DELETE` and `UPDATE` privileges are revoked from the application database role.
- Monthly range partitions for efficient archival.
- Archived to S3 Glacier after 90 days (configurable). Retained minimum 7 years.
- Tamper detection: each row includes a SHA-256 hash of `(prev_row_hash || payload)`, forming an audit chain. Integrity verified by the auditor API endpoint.

### Encryption

| Data | At Rest | In Transit |
|---|---|---|
| Database | PostgreSQL TDE via cloud provider (or LUKS on-prem) | TLS 1.3 required, SSL mode=require |
| Secrets (API keys, credentials) | Vault-encrypted, never in DB | Vault transit engine (envelope encryption) |
| Memory records | Column-level encryption for CONFIDENTIAL access level rows | TLS |
| Session transcripts (S3) | SSE-S3 or SSE-KMS | HTTPS only |
| Redis | Encrypted in transit (TLS), encrypted at rest via cloud provider | TLS required |
| Agent JWTs | RS256-signed, 15-min TTL | HTTPS only |

### Prompt Injection Defense (from Claude Code lessons)
Claude Code documented CVE-2025-54794/54795 (InversePrompt). Helix mitigations:
- Tool outputs processed through a sanitization pass before injecting into agent context. Pattern-based detection of role-switch attempts, system prompt override attempts, and `<instructions>` tag injection.
- Integration tool results are wrapped in a `[TOOL RESULT - UNTRUSTED]` delimiter in the agent context window, with an explicit system prompt instruction that content within these delimiters cannot override instructions.
- A separate Haiku inference call evaluates suspicious tool outputs before they are shown to the primary agent (same pattern as Claude Code's permission explainer sandboxed LLM call).

---

## Scaling Considerations

### What Breaks First

1. **LLM gateway throughput (first bottleneck):** Each agent makes multiple LLM calls. A workflow with 5 parallel workers × 10 turns × 3s per call = heavy concurrent Anthropic API load. Anthropic rate limits are per-org. Mitigation: per-tenant token bucket rate limiting in Redis, request queuing in Celery, priority queue for CRITICAL workflows.

2. **PostgreSQL write throughput on audit_events:** High-volume orgs generate thousands of audit events per minute. Mitigation: `audit_events` is range-partitioned by month. Write path uses a buffer (Redis list) that flushes to DB in batches every 500ms via Celery. Audit latency (not immediacy) is acceptable for SOC 2.

3. **pgvector index performance at scale:** IVFFlat index degrades above ~1M vectors per org. Mitigation: partition `memory_records` by `org_id`. For orgs approaching 100K+ memory records, migrate to HNSW index (`CREATE INDEX USING hnsw`). HNSW has better query performance at the cost of higher build time and memory.

4. **Celery worker saturation during multi-org dream cycles:** If many orgs trigger consolidation simultaneously, the Celery pool starves. Mitigation: separate Celery queues for `dream_cycle` (low priority, long tasks) and `workflow_execution` (high priority, latency-sensitive). Dream cycle workers are a separate autoscaling group.

5. **Redis memory on pub/sub with many concurrent workflows:** Each active workflow holds a Redis pub/sub channel. At 10K concurrent workflows, channel overhead is significant. Mitigation: channel pooling, expiry on idle channels, upgrade to Redis Cluster for horizontal shaling beyond 64GB.

### Horizontal vs Vertical

| Component | Scale Direction | Notes |
|---|---|---|
| FastAPI control plane | Horizontal (stateless) | Session state in Redis, any instance handles any request |
| LangGraph orchestration workers | Horizontal | Each worker handles one workflow; Celery task queue distributes |
| LLM Gateway | Horizontal | Pure function — no state. Scale with workflow workers |
| Dream Cycle workers | Horizontal (separate pool) | Isolated from real-time workflows |
| PostgreSQL | Vertical first, then read replicas | Write bottleneck on audit_events; consider Citus for sharding at extreme scale |
| pgvector | Vertical (memory-intensive) | HNSW index is RAM-resident; size instance to fit all active org indexes |
| Redis | Horizontal (Redis Cluster) | Shard by key prefix: `rate_limit:`, `pubsub:`, `session:` on separate shards |

---

## Key Architecture Decisions

**1. LangGraph over custom FSM for orchestration.**
Claude Code's coordinator uses a custom TypeScript state machine. Building a comparable system from scratch is 6+ months of work. LangGraph provides a production-grade typed state machine with built-in persistence, interrupt/resume support (critical for HITL approval flows), and streaming. The LangGraph checkpoint system maps cleanly to our `workflows` table.

**2. PostgreSQL IPC over file-based messages.**
Claude Code's `agent_messages` use filesystem paths (`~/.claude/teams/{team}/{session}/`). This does not scale beyond a single machine and has race conditions on file locks. PostgreSQL with `LISTEN/NOTIFY` + Redis pub/sub provides distributed, ordered, durable IPC. The tradeoff is latency (~2ms vs ~0.1ms for file ops), which is irrelevant at agent turn timescales.

**3. Database savepoints over overlay filesystem for speculation.**
Claude Code's speculative execution uses a userspace overlay filesystem — no kernel-level isolation, vulnerable to escape (documented by Anthropic). PostgreSQL savepoints are ACID-safe and naturally distributed. Any node in the cluster can resume a speculative workflow. Rollback is atomic. The constraint: speculative integration calls that are read-only must not have side effects (enforced by `IntegrationTool.idempotent` flag).

**4. pgvector semantic retrieval over keyword-based relevance selection.**
Claude Code's Sonnet-powered selector reads up to 5 memory files using keyword matching — sequential file reads, O(N) scanning. A single `SELECT ... ORDER BY embedding <=> $query_vec LIMIT 10` query is O(log N) with IVFFlat and returns semantically relevant results, not just lexically matching ones. Critical for enterprise workflows where the same concept appears under many different names.

**5. Transparent model fallback over Claude Code's silent downgrades.**
Claude Code silently switches Opus → Sonnet on 529 errors with no user notification. In enterprise, silent quality degradation on critical workflows (e.g., a contract review agent) is a support and compliance problem. Helix emits `model_fallback` audit events and optionally surfaces the degradation to operators via webhook. The `allow_silent_downgrade` policy flag lets orgs opt into Claude Code behavior if latency matters more than transparency.

**6. Row Level Security as defense-in-depth, not sole control.**
Multi-tenant systems that rely only on application-layer `WHERE org_id = X` are one ORM bug away from a data breach. RLS at the database layer means even a SQL injection through the application cannot return cross-tenant rows. The performance overhead is ~3-5% on indexed queries — acceptable for the isolation guarantee.

**7. Configurable hierarchy depth over Claude Code's hard-coded one level.**
Claude Code hard-codes single-level subagent hierarchy (workers cannot spawn workers). This is safe for a consumer coding tool but too restrictive for enterprise workflows: a research agent may need to spawn domain-specific sub-researchers, which in turn spawn data fetchers. Helix allows configurable `max_hierarchy_depth` per workflow template (default: 2, max: 4). Depth enforcement is in the orchestration engine, not the agent prompt — cannot be overridden by a prompt injection.

**8. Composio/Nango for integration connectors over building OAuth infrastructure.**
Claude Code builds every integration from scratch (each tool is a bespoke implementation). For enterprise SaaS coverage (Salesforce, SAP, Oracle, Workday, ServiceNow), building and maintaining OAuth flows, token refresh, webhook registration, and API versioning is 12+ months of dedicated engineering. Composio provides 250+ managed connectors with standardized tool schemas. The risk is vendor lock-in; Nango as an alternative maintains leverage.

**9. Append-only audit trail with chain hashing for SOC 2 compliance.**
Claude Code has no audit trail — it is a single-user tool. Enterprise customers face SOC 2 Type II requirements that mandate immutable logs with tamper evidence. The chain-hashing approach (each event hashes the previous event's hash) provides tamper detection without the overhead of a blockchain. Partitioned by month for retention policy enforcement and archival.

**10. Separate Celery queues for real-time and background workloads.**
Claude Code's autoDream runs as a forked subagent in the main process — it can compete with the user's active session for CPU. Helix isolates Dream Cycle workers in a separate queue and autoscaling group. Real-time workflow execution (latency-sensitive) is never delayed by a consolidation run. This is the enterprise adaptation of Claude Code's "forked read-only subagent" pattern — same isolation principle, different mechanism.
