# Connector & Data Pipeline Architecture for Helix

**Date:** 2026-03-31

## BLUF

Build a 3-layer connector system: **Nango** for OAuth/auth management (self-hosted, open source), **MCP servers** for agent tool exposure (one per connector family), and a **continuous ingest pipeline** (webhooks + Unstructured.io + pgai Vectorizer) that feeds SaaS data into memory without agents having to ask. Keep Composio for the existing 10 stubs while migrating. Defer knowledge graph to V2 — pgvector alone is sufficient to launch.

---

## The Three Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    LAYER 1: AUTH (Nango)                     │
│  OAuth 2.0 management · Token refresh · Per-tenant scoping  │
│  400+ providers · Self-hosted · OpenTelemetry on every call  │
└────────────────────────┬────────────────────────────────────┘
                         │ Fresh tokens
┌────────────────────────▼────────────────────────────────────┐
│               LAYER 2: TOOLS (MCP Servers)                   │
│  One FastAPI MCP server per connector family                 │
│  Agent discovers tools via tools/list                        │
│  Agent calls tools via tools/call                            │
│  LangGraph binds via langchain-mcp-adapters                  │
│  Tool router: task context → ≤15 relevant tools              │
└────────────────────────┬────────────────────────────────────┘
                         │ Structured outputs
┌────────────────────────▼────────────────────────────────────┐
│           LAYER 3: MEMORY PIPELINE (Continuous)              │
│                                                              │
│  Webhooks ──→ Unstructured.io ──→ document_staging table     │
│  Polling  ──→    (normalize)  ──→    (chunk + metadata)      │
│  CDC      ──→                 ──→    (content hash dedup)    │
│                                                              │
│  pgai Vectorizer ──→ embed ──→ memory_vectors table          │
│  (watches via logical replication, auto-embeds new rows)     │
│                                                              │
│  Dream Cycle reads from memory_vectors (pre-indexed)         │
│  Agents query memory_vectors at runtime (ambient awareness)  │
└─────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Auth — Nango

**Why Nango over Composio for auth:** Self-hostable (Elastic License), open source, 400+ OAuth providers, automatic token refresh with OpenTelemetry traces, per-user multi-tenant credentials. Composio is cloud-only below Enterprise tier.

**Pricing:** Self-hosted free (OSS), Cloud $250/mo (20 connections, $1/overage), Enterprise annual license for on-prem.

**How it works:**
```python
# User clicks "Connect Salesforce" in UI
auth_url = nango.get_connect_url(provider="salesforce", connection_id=f"{org_id}:{user_id}")
# → Redirect to Salesforce OAuth consent screen
# → Nango handles callback, stores encrypted tokens

# Agent needs to call Salesforce API
token = nango.get_token(provider="salesforce", connection_id=f"{org_id}:{user_id}")
# → Returns fresh access token, auto-refreshed if expired
```

---

## Layer 2: Tools — MCP Servers

**Why MCP:** De facto standard (97M+ monthly SDK downloads). Backed by OpenAI, Anthropic, Google, Microsoft. `langchain-mcp-adapters` converts MCP tools to LangGraph `BaseTool` with zero custom code.

**Architecture:** One FastAPI MCP server per connector family, running inside Helix infrastructure (never public).

### Connector Definition Schema

```python
class ConnectorDefinition(BaseModel):
    """Defines a prebuilt connector with tools and sync streams."""
    id: str                           # "salesforce"
    display_name: str                 # "Salesforce"
    auth_provider: str                # Nango provider key
    categories: list[str]             # ["crm", "sales"]
    tools: list[ToolDefinition]
    sync_streams: list[SyncStream]

class ToolDefinition(BaseModel):
    """A single tool callable by agents via MCP."""
    name: str                         # "salesforce_get_account"
    description: str                  # LLM-optimized natural language
    parameters: dict                  # JSON Schema
    risk_level: str                   # LOW | MEDIUM | HIGH | CRITICAL
    requires_approval: bool
    read_only: bool                   # Safe for speculative execution

class SyncStream(BaseModel):
    """A data stream that feeds into memory continuously."""
    name: str                         # "opportunities"
    entity_type: str                  # For memory tagging
    sync_method: str                  # "webhook" | "polling" | "cdc"
    sync_frequency: str               # "realtime" | "10m" | "1h" | "daily"
    fields_to_index: list[str]        # Which fields to embed
    acl_field: str | None             # Field containing access control info
```

### Tool Router (Critical for Scale)

Passing 500 tool definitions into a single LLM context window is prohibitively expensive. A tool router selects 5-15 relevant tools based on:
- User's connected integrations
- Current workflow/task context
- Tool usage history

```python
async def route_tools(org_id: str, task_description: str, max_tools: int = 15) -> list[ToolDefinition]:
    """Select relevant tools for the current task from all available."""
    connected = await get_connected_integrations(org_id)
    all_tools = [t for c in connected for t in get_tools(c.provider)]
    # Use Haiku to rank relevance, or keyword matching for zero-cost
    return rank_by_relevance(all_tools, task_description)[:max_tools]
```

### LangGraph Integration

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_agent_tools(org_id: str) -> list[BaseTool]:
    """Get MCP tools for all connected integrations."""
    connected = await get_connected_integrations(org_id)
    servers = {c.provider: {"url": f"http://mcp-{c.provider}:8080/sse"} for c in connected}
    client = MultiServerMCPClient(servers)
    return await client.get_tools()
```

---

## Layer 3: Memory Pipeline — Continuous Ingest

### Sync Method Per Integration

| Integration | Method | What to Index | Frequency |
|---|---|---|---|
| **Slack** | Webhook (Events API) | Channel messages, thread replies, pinned items | Real-time |
| **GitHub** | Webhook | Issues, PRs, review comments, docs/README | Real-time |
| **Jira** | Webhook | Issues + comments, sprint goals, epic descriptions | Real-time |
| **Salesforce** | Streaming API (CDC) | Accounts, Opps, Cases, Contacts, activity notes | Real-time |
| **HubSpot** | Webhook | Deals, Contacts, Notes, timeline events | Real-time |
| **Zendesk** | Webhook | Tickets + comments + resolution, KB articles | Real-time |
| **Google Workspace** | Push notifications | Docs full text, Calendar events, Sheet summaries | Real-time |
| **DocuSign** | Webhook (Connect) | Envelope metadata, AI-extracted clauses (Navigator) | Real-time |
| **ServiceNow** | Polling | Incidents, KB articles, change requests | Every 15m |
| **Notion** | Polling (no webhooks) | Pages, database entries | Every 10m |

### Pipeline Architecture

```
SaaS Event (webhook/poll/CDC)
    │
    ▼
FastAPI Webhook Receiver (verify signature)
    │
    ▼
Redis Queue (ARQ or Celery)
    │
    ▼
Worker: Unstructured.io (in-process, OSS)
    ├── Normalize content → Element schema
    ├── Chunk (semantic boundaries, not fixed-size)
    ├── Extract metadata (source, ACL, entity type)
    ├── SHA-256 content hash for dedup
    └── Write to document_staging table
              │
              ▼
    pgai Vectorizer (watches via logical replication)
    ├── Skip unchanged content (hash match)
    ├── Embed with text-embedding-3-small
    └── Upsert into memory_vectors (pgvector)
              │
              ▼
    Available to:
    ├── Agent runtime queries (ambient awareness)
    ├── Dream Cycle Orient phase (pre-indexed)
    └── Semantic memory search API
```

### New Database Tables

```sql
-- Staged documents before embedding
CREATE TABLE document_staging (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    source_system VARCHAR(64) NOT NULL,      -- "slack", "salesforce", etc.
    source_id VARCHAR(512) NOT NULL,         -- External ID
    source_url TEXT,                          -- Link back to original
    entity_type VARCHAR(128),                -- "message", "ticket", "opportunity"
    title TEXT,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,       -- SHA-256 for dedup
    acl_metadata JSONB DEFAULT '{}',         -- Permissions context
    metadata JSONB DEFAULT '{}',             -- Source-specific fields
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, source_system, source_id)
);

-- Vectors auto-managed by pgai Vectorizer
CREATE TABLE memory_vectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES orgs(id),
    document_id UUID NOT NULL REFERENCES document_staging(id),
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(1536),
    embedding_model VARCHAR(64) NOT NULL,    -- Version tracking for migration
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_memory_vectors_org ON memory_vectors
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### ACL Enforcement at Retrieval Time

```python
async def search_memory_with_acl(
    session: AsyncSession, org_id: UUID, query_vec: list[float],
    user_roles: list[str], limit: int = 10,
) -> list[dict]:
    """Semantic search with permission filtering."""
    result = await session.execute(text("""
        SELECT mv.chunk_text, mv.embedding <=> :vec::vector AS distance,
               ds.source_system, ds.entity_type, ds.source_url, ds.acl_metadata
        FROM memory_vectors mv
        JOIN document_staging ds ON ds.id = mv.document_id
        WHERE mv.org_id = :org_id
          AND ds.acl_metadata->>'visibility' IN ('public', 'shared')
        ORDER BY mv.embedding <=> :vec::vector
        LIMIT :limit
    """), {"org_id": org_id, "vec": str(query_vec), "limit": limit})
    return [dict(row) for row in result.fetchall()]
```

---

## Migration Path

| Phase | Action | Timeline |
|---|---|---|
| **Now** | Keep Composio for existing 10 tool stubs | Already working |
| **Week 1** | Stand up Nango self-hosted, migrate Salesforce OAuth | Auth layer independent |
| **Week 2** | Build first MCP server (Salesforce) with Nango tokens | Proves the pattern |
| **Week 3** | Deploy webhook receivers for Slack + GitHub | Highest-velocity data |
| **Week 4** | Add Unstructured.io + pgai Vectorizer pipeline | Memory starts filling |
| **Week 5-6** | Migrate remaining 8 integrations to Nango + MCP | One per day pace |
| **Week 7** | Build tool router middleware | Agent efficiency |
| **Week 8** | Add Airbyte for historical backfill | Full memory coverage |
| **V2** | Add FalkorDB/Neo4j graph layer to Dream Cycle | Relationship-aware memory |

---

## Key Decisions

1. **Nango for auth, not Composio** — self-hostable, open source, we control the tokens
2. **MCP for tool exposure** — de facto standard, LangGraph native adapter, no custom wrappers
3. **Webhooks for 8/10 integrations** — real-time, not polling. Notion and ServiceNow are the exceptions
4. **Unstructured.io for normalization** — consistent Element schema across all sources, handles PDFs/HTML/JSON
5. **pgai Vectorizer for continuous embedding** — eliminates custom embedding worker, uses PostgreSQL logical replication
6. **Content hashing for dedup** — SHA-256 of content before embedding, skip unchanged records
7. **ACL metadata at ingest, enforce at retrieval** — never index without permission context
8. **Defer knowledge graph to V2** — pgvector alone is sufficient to launch; add graph for Dream Cycle entity extraction later
9. **Embedding model version tracking** — `embedding_model VARCHAR(64)` from day one for migration safety
10. **Tool router for scale** — 5-15 tools per task, not 500 in context window

---

## Open Questions

1. **Permission granularity**: Workspace-wide institutional memory or per-user ACL enforcement? (Determines pipeline complexity significantly)
2. **Notion webhooks**: Expected to ship 2026 — monitor changelog
3. **DocuSign Navigator**: What % of customers have it? Determines clause extraction vs metadata-only
4. **Embedding model**: text-embedding-3-small (cheaper) vs text-embedding-3-large (better for long docs)?
5. **Salesforce edition**: Enterprise (CDC available) vs Professional (polling only) — customer base distribution?

---

## Sources

- [Nango Pricing & Self-Hosting](https://nango.dev/pricing)
- [Composio MCP & Enterprise](https://composio.dev/enterprise)
- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [LangChain MCP Adapters](https://github.com/langchain-ai/langchain-mcp-adapters)
- [Unstructured.io Enterprise RAG](https://unstructured.io/blog/enterprise-rag-why-connectors-matter)
- [pgai Vectorizer (Timescale)](https://github.com/timescale/pgai)
- [Airbyte pgvector Destination](https://docs.airbyte.com/integrations/destinations/pgvector)
- [Glean Knowledge Graph Architecture](https://www.glean.com/blog/knowledge-graph-agentic-engine)
- [Dust.tt MCP + Enterprise Agents](https://blog.dust.tt/mcp-and-enterprise-agents-building-the-ai-operating-system-for-work/)
- [Cognee Memory Engine](https://github.com/topoteretes/cognee)
- [MCP Security Risks](https://prompt.security/blog/top-10-mcp-security-risks)
