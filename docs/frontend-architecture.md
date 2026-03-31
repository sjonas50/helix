# Architecture: Helix Frontend

## System Overview

Helix frontend is a Next.js 15 BFF (Backend-for-Frontend) that proxies REST calls to FastAPI while the browser maintains a direct WebSocket connection to FastAPI for real-time events. WorkOS AuthKit handles SSO with a redirect-based flow. The UI is built for non-technical enterprise users (sales ops, HR, finance, CS managers) — every design decision prioritizes trust and legibility over power-user density.

```
┌─────────────────────────────────────────────────────────────────────┐
│                           BROWSER                                   │
│                                                                     │
│  ┌──────────────┐    ┌───────────────┐    ┌────────────────────┐   │
│  │  React Pages │    │ TanStack Query│    │  Zustand Stores    │   │
│  │  (App Router)│    │ (server state)│    │  (UI/client state) │   │
│  └──────┬───────┘    └───────┬───────┘    └────────────────────┘   │
│         │                   │                                       │
│  ┌──────▼───────────────────▼───────────────────────────────────┐  │
│  │              WorkOS AuthKit (session + JWT mgmt)             │  │
│  └──────┬───────────────────────────────────────────────────────┘  │
│         │                                                           │
│         │  HTTPS (REST)              WSS (WebSocket)               │
└─────────┼────────────────────────────────┬────────────────────────┘
          │                                │
          ▼                                │
┌─────────────────────┐                   │
│  Next.js 15         │                   │
│  (standalone, K8s)  │                   │
│                     │                   │
│  /api/proxy/*  ──────────► FastAPI REST │
│  /api/auth/*  (WorkOS cb)  /api/v1/*    │
│  React SSR/CSR             (24+ endpoints)
│  Static assets             │            │
└─────────────────────┘      │            │
                             │            ▼
                    ┌────────┴────────────────────┐
                    │       FastAPI                │
                    │  /api/v1/ws?token=<jwt>      │
                    │  ├─ approval_request (push)  │
                    │  ├─ workflow_status (push)   │
                    │  ├─ agent_activity (push)    │
                    │  └─ approve/reject (recv)    │
                    └─────────────────────────────┘

SSO Flow:
Browser ──► WorkOS AuthKit ──► [enterprise IdP] ──► WorkOS callback
       ◄── redirect ─────────────────────────────────────────────────
Next.js /api/auth/callback ──► exchange code ──► JWT set in cookie
```

---

## Directory Structure

```
frontend/
├── app/                            # Next.js App Router
│   ├── (auth)/
│   │   ├── login/
│   │   │   └── page.tsx            # WorkOS AuthKit redirect trigger
│   │   └── callback/
│   │       └── page.tsx            # WorkOS code exchange handler
│   ├── (dashboard)/                # Route group: requires auth
│   │   ├── workflows/
│   │   │   ├── page.tsx            # Workflow gallery (template browser)
│   │   │   ├── new/
│   │   │   │   └── page.tsx        # NL creator + canvas preview
│   │   │   └── [id]/
│   │   │       ├── page.tsx        # Workflow canvas editor
│   │   │       └── runs/
│   │   │           └── page.tsx    # Execution history for one workflow
│   │   ├── approvals/
│   │   │   └── page.tsx            # Approval queue
│   │   ├── memory/
│   │   │   └── page.tsx            # Memory browser + semantic search
│   │   ├── integrations/
│   │   │   └── page.tsx            # Integration hub + OAuth flows
│   │   ├── audit/
│   │   │   └── page.tsx            # Audit trail table + undo
│   │   ├── settings/
│   │   │   ├── page.tsx            # General org settings
│   │   │   ├── autonomy/
│   │   │   │   └── page.tsx        # Per-workflow autonomy dial management
│   │   │   ├── members/
│   │   │   │   └── page.tsx        # RBAC / user management
│   │   │   └── billing/
│   │   │       └── page.tsx        # Usage charts, cost attribution
│   │   └── page.tsx                # Dashboard home
│   ├── layout.tsx                  # Root layout: QueryClientProvider, ZustandProvider, WSProvider
│   ├── globals.css                 # Tailwind base
│   └── page.tsx                    # Root redirect → /login or /dashboard
├── components/
│   ├── ui/                         # shadcn/ui copied components (Button, Card, Dialog, etc.)
│   ├── workflow/
│   │   ├── Canvas.tsx              # React Flow wrapper with dagre auto-layout
│   │   ├── nodes/
│   │   │   ├── TriggerNode.tsx
│   │   │   ├── ActionNode.tsx
│   │   │   ├── ConditionNode.tsx
│   │   │   ├── ApprovalNode.tsx    # HITL pause point
│   │   │   └── AgentNode.tsx
│   │   ├── edges/
│   │   │   └── LabeledEdge.tsx
│   │   ├── NodeConfigPanel.tsx     # Slide-in config for selected node
│   │   ├── NLCreator.tsx           # Text input → AI generation → canvas preview
│   │   ├── AutonomyBadge.tsx       # Inline dial indicator on canvas header
│   │   └── TestRunPanel.tsx        # Sandbox run UI + result diff view
│   ├── approval/
│   │   ├── ApprovalCard.tsx        # Single card: action, reasoning, 3-way decision
│   │   ├── ApprovalQueue.tsx       # Sorted list with batch actions
│   │   ├── ModifyDrawer.tsx        # Inline edit triggered by "Modify" action
│   │   └── ApprovalBadge.tsx       # Pending count badge for nav
│   ├── memory/
│   │   ├── MemorySearch.tsx        # Semantic search input + results
│   │   ├── TopicTree.tsx           # Hierarchical topic browser
│   │   └── MemoryCard.tsx          # Single memory entry with access level badge
│   └── shared/
│       ├── AppShell.tsx            # Sidebar + header layout wrapper
│       ├── Sidebar.tsx             # Nav links, pending approval badge
│       ├── Header.tsx              # Org switcher, user menu, notifications bell
│       ├── AutonomyDial.tsx        # 4-position dial component (reused in settings + canvas)
│       ├── AuditEntry.tsx          # Single audit log row: plain-English + optional Undo
│       ├── ErrorBoundary.tsx       # Plain-English error fallback (no stack traces to users)
│       └── WSStatusIndicator.tsx   # Connection health dot in header
├── lib/
│   ├── api/
│   │   ├── client.ts               # Fetch wrapper: attaches JWT, handles 401, base URL
│   │   ├── workflows.ts            # useWorkflows, useWorkflow, useCreateWorkflow, useDeployWorkflow
│   │   ├── approvals.ts            # useApprovals, useApproveAction, useRejectAction, useModifyAction
│   │   ├── executions.ts           # useExecutions, useExecution, useRunWorkflow
│   │   ├── memory.ts               # useMemorySearch, useMemoryTopics, useMemoryEntry
│   │   ├── integrations.ts         # useIntegrations, useConnectIntegration, useDisconnectIntegration
│   │   ├── audit.ts                # useAuditLog, useUndoAction
│   │   ├── agents.ts               # useAgents, useAgentActivity
│   │   └── settings.ts             # useOrgSettings, useAutonomySettings, useUsageStats
│   ├── ws/
│   │   ├── useHelixWebSocket.ts    # react-use-websocket wrapper: JWT handshake, reconnect, event dispatch
│   │   └── wsEventHandlers.ts      # Map event type → queryClient.invalidateQueries
│   ├── auth/
│   │   ├── workos.ts               # WorkOS AuthKit server-side client (authkitMiddleware config)
│   │   ├── useAuth.ts              # Client-side auth hook: session, user, org_id from JWT
│   │   └── guards.ts               # Route guard HOC + role check utilities
│   └── store/
│       ├── uiStore.ts              # Sidebar collapsed, active modal, notification drawer open
│       ├── workflowStore.ts        # Canvas node selection, unsaved changes, NL input state
│       └── wsStore.ts              # WebSocket connection status, last event timestamp
├── types/
│   ├── api.ts                      # Mirrors FastAPI Pydantic schemas (Workflow, Execution, Approval, etc.)
│   ├── ws.ts                       # WebSocket event union type
│   └── auth.ts                     # JWT claims shape, WorkOS user type
├── middleware.ts                   # Next.js middleware: authkitMiddleware for (dashboard) routes
├── tests/
│   ├── unit/                       # Vitest: store logic, API hook transforms, util functions
│   ├── components/                 # Vitest + @testing-library/react: component rendering
│   │   └── __mocks__/              # MSW handlers for REST + WS mocks
│   └── e2e/                        # Playwright: full login → workflow create → approve flows
├── next.config.ts                  # output: 'standalone', rewrites for /api/proxy
├── pyproject.toml                  # (root) — frontend lives in /frontend subdirectory
├── .env.example
├── Dockerfile
└── docker-compose.yml
```

---

## Component Breakdown

### Dashboard (`app/(dashboard)/page.tsx`)

Primary user: all roles. First screen after login.

- **Activity Feed** — Scrollable list of `AuditEntry` components showing the last 20 agent actions across all workflows in the org. Each entry links to the relevant workflow or approval. Sourced from `useAuditLog({ limit: 20 })` with 30-second polling interval as fallback to WebSocket.
- **Pending Approvals Count** — `ApprovalBadge` in the header and a prominent card widget. Clicking navigates to `/approvals`. Count is updated immediately on `approval_request` WebSocket events via query invalidation.
- **Active Workflows** — Summary cards: workflow name, last run time, autonomy level, current status (idle / running / waiting for approval). Sourced from `useWorkflows({ status: 'active' })`.
- **Quick Actions** — "Create Workflow" button (navigates to `/workflows/new`), "View All Approvals" button. Role-gated: builder role sees "Create", approver-only role sees approvals prominently.

State: no local state beyond what TanStack Query provides. WebSocket events invalidate `['approvals']` and `['audit']` query keys.

---

### Workflow Gallery (`app/(dashboard)/workflows/page.tsx`)

Primary user: builder (ops specialist).

- **Template Cards** — Grid of cards. Each card: workflow name, plain-English description, estimated setup time, role badge (Sales Ops / HR / Finance / CS), "Use Template" CTA. Minimum 20 templates at launch across 4 personas.
- **Role Filter** — Pill filters at top. Default: filtered to current user's role (derived from JWT `role` claim). Overridable. Filter state stored in URL query params (`?role=sales_ops`) for shareability.
- **NL Creator Entry Point** — Prominent "Describe a workflow" input at top of page. On submit, navigates to `/workflows/new?prompt=<encoded>` and triggers `NLCreator` component pre-populated with the input.
- **My Workflows Tab** — Lists workflows owned by the current user's org. Sortable by last run, creation date, name.

Data: `useWorkflows()` for org workflows; templates are static JSON seeded in `lib/api/templates.ts` (no backend call needed at launch).

---

### Workflow Canvas (`app/(dashboard)/workflows/[id]/page.tsx` and `/workflows/new`)

Primary user: builder.

- **NLCreator (`components/workflow/NLCreator.tsx`)** — Text area + submit. On submit, calls `POST /api/v1/workflows/generate` (via BFF proxy). Streams back a `WorkflowDraft` with nodes and edges. Canvas renders the draft immediately. Shows a "Generating..." skeleton during streaming. If AI returns a `clarification_needed` field, renders a follow-up question before proceeding.
- **Canvas (`components/workflow/Canvas.tsx`)** — React Flow canvas with `@xyflow/react` v12. Nodes: Trigger, Action, Condition, ApprovalNode (HITL pause), AgentNode. Edges: `LabeledEdge` with plain-English transition labels. `dagre` auto-layout on first render; user can drag after that.
- **NodeConfigPanel** — Slide-in panel (shadcn Sheet) on node click. Shows node-specific fields. Form built with React Hook Form + Zod. Saves to workflow draft in `workflowStore`.
- **AutonomyBadge** — Displays current autonomy level in canvas header. Clicking navigates to settings. Read from `useWorkflow(id).data.autonomy_level`.
- **TestRunPanel** — "Test Run" button in toolbar opens a bottom drawer. Runs workflow against sandbox data (`POST /api/v1/workflows/{id}/test`). Shows diff: what would have happened vs. real data. Pass/fail per node.
- **Deploy Button** — Disabled until all nodes are valid (Zod-validated). On click: `PATCH /api/v1/workflows/{id}` with status `active`. Redirects to workflow detail / dashboard on success.

State: Canvas node positions and unsaved edits live in `workflowStore`. On deploy, the store is flushed.

---

### Approval Queue (`app/(dashboard)/approvals/page.tsx`)

Primary user: approver (manager).

- **Card List** — Sorted by urgency (time limit ASC). Each `ApprovalCard` shows: agent name, proposed action in plain English, trigger context ("This was triggered because..."), consequence preview ("If approved: X / If rejected: Y"), time remaining, confidence signal (Low / Medium / High badge).
- **3-Way Decision** — "Approve" (green), "Reject" (red), "Modify" (secondary) buttons on each card. "Modify" opens `ModifyDrawer` with editable fields pre-populated from the approval request.
- **Optimistic Updates** — On approve/reject, the card is immediately removed from the list (`optimisticUpdate` via TanStack Query). If the API call fails, the card is restored with an error toast.
- **Batch Actions** — Checkbox multi-select on cards. "Approve All Selected" / "Reject All Selected" batch action bar appears at bottom when 2+ cards are selected. Calls `POST /api/v1/approvals/batch`.
- **Empty State** — "No pending approvals. Your agents are working autonomously." with a link to the audit trail.

Real-time: New cards appear without page refresh via `approval_request` WebSocket event → `queryClient.invalidateQueries(['approvals'])`.

---

### Memory Browser (`app/(dashboard)/memory/page.tsx`)

Primary user: builder, auditor.

- **Semantic Search** — Input at top. On submit (debounced 300ms), calls `GET /api/v1/memory/search?q=<query>&org_id=<org>`. Results ranked by semantic similarity score. Each result shows: title, excerpt, source workflow, last updated, access level badge.
- **Topic Tree** — Left sidebar: hierarchical taxonomy of memory topics (e.g., "Customer Data > Acme Corp > Contacts"). Clicking a topic filters results. Sourced from `GET /api/v1/memory/topics`.
- **Access Level Badges** — Each memory card shows: `org-wide`, `workflow-scoped`, or `agent-private`. Color-coded. Non-admin users cannot see `agent-private` entries (filtered server-side, badge for transparency).
- **Memory Card Actions** — "View Full", "Delete" (admin only), "Export". Delete is confirmation-gated via shadcn AlertDialog.

---

### Audit Trail (`app/(dashboard)/audit/page.tsx`)

Primary user: auditor, manager.

- **Paginated Table** — TanStack Table v8. Columns: Timestamp, Actor (agent name), Action (plain English), Workflow, Status, Reversible. Server-side pagination via `GET /api/v1/audit?page=N&limit=50`.
- **Filters** — Date range picker, workflow multiselect, action type filter, "show escalations only" toggle. Filter state in URL query params.
- **Plain-English Entries** — Every row is human-readable. Technical details (HTTP status, etc.) are in a collapsible "Technical details" section, hidden by default.
- **Undo Button** — Rows where `reversible: true` show an "Undo" button with a countdown timer (if time-limited). Clicking triggers `POST /api/v1/audit/{entry_id}/undo` with optimistic row update to `reversing...` status.
- **Integrity Check** — "Verify Integrity" button in header calls `GET /api/v1/audit/integrity`. Displays a green checkmark or a specific entry where the chain broke.
- **Escalation Highlight** — Rows where `event_type: escalation` are highlighted with a positive framing tooltip: "Agent asked for human review — this is expected behavior."

---

### Integration Hub (`app/(dashboard)/integrations/page.tsx`)

Primary user: builder, admin.

- **Integration Cards** — Grid. Each card: service logo, name, connection status (Connected / Disconnected / Error), last sync time, risk level badge (Low / Medium / High based on permission scope). "Connect" / "Reconnect" / "Disconnect" actions.
- **OAuth Flow** — "Connect" triggers `GET /api/v1/integrations/{slug}/auth-url`. Browser navigates to the OAuth provider. Callback returns to `/api/v1/integrations/{slug}/callback` (FastAPI handles token exchange). Frontend polls `useIntegration(slug)` for status change after redirect.
- **Tool Discovery** — "Browse Available Integrations" section shows unconnected integrations categorized by type (CRM, Email, Docs, Calendar, etc.).
- **Error State** — If an integration has `status: error`, the card shows the plain-English reason ("Gmail disconnected — token expired") with a "Reconnect" CTA. This same error format appears in audit entries and approval cards that reference the broken integration.

---

### Settings (`app/(dashboard)/settings/`)

Primary user: admin.

- **Autonomy Management (`/settings/autonomy`)** — Table of all active workflows with their current autonomy level. `AutonomyDial` component inline per row (4-position: Observe & Suggest / Plan & Propose / Act with Confirmation / Act Autonomously). Updating a dial calls `PATCH /api/v1/workflows/{id}` with `autonomy_level`. "Suggest upgrade" banner appears on workflows with 5+ consecutive approvals.
- **Members & RBAC (`/settings/members`)** — User table with role assignment (Admin / Builder / Approver / Auditor). Invite by email (WorkOS-handled). Role changes call `PATCH /api/v1/org/members/{user_id}`.
- **Billing & Usage (`/settings/billing`)** — Token usage over time (Recharts line chart). Cost attribution per workflow (bar chart). Usage by agent. Trend vs. previous period. Data from `GET /api/v1/usage/stats`.
- **General Org Settings** — Org name, default autonomy level for new workflows, notification preferences (Slack webhook URL, Teams webhook URL).

---

## Data Flow Sequences

### 1. NL Workflow Creation

```
1. User types intent into NLCreator textarea
2. Submit → POST /api/proxy/workflows/generate (Next.js BFF → FastAPI)
3. FastAPI streams WorkflowDraft (nodes[], edges[], clarification_needed?)
4. If clarification_needed: render follow-up question, await user response, re-POST
5. NLCreator receives final WorkflowDraft, writes to workflowStore.draftWorkflow
6. Canvas renders nodes/edges from store with dagre auto-layout
7. User inspects canvas, clicks nodes to open NodeConfigPanel, edits
8. NodeConfigPanel writes changes back to workflowStore.draftWorkflow
9. User clicks "Test Run" → POST /api/proxy/workflows/test with draft
10. TestRunPanel renders per-node pass/fail diff
11. User clicks "Deploy" → POST /api/proxy/workflows (create) or PATCH /api/proxy/workflows/{id}
12. On success: workflowStore.draftWorkflow cleared, navigate to /workflows/{id}
13. queryClient.invalidateQueries(['workflows']) refreshes gallery
```

### 2. Approval Flow

```
1. Agent hits HITL checkpoint during execution (FastAPI)
2. FastAPI pushes approval_request event over WebSocket to all connected org members
3. useHelixWebSocket receives event, calls wsEventHandlers.onApprovalRequest
4. wsEventHandlers calls queryClient.invalidateQueries(['approvals'])
5. ApprovalQueue re-fetches GET /api/proxy/approvals → new card appears
6. User clicks "Approve" on ApprovalCard
7. Optimistic update: card removed from UI immediately
8. POST /api/proxy/approvals/{id}/approve fires in background
9a. On success: nothing (optimistic state already correct)
9b. On failure: queryClient.invalidateQueries(['approvals']), toast error, card restored
10. FastAPI resumes workflow execution
11. workflow_status WebSocket event fires → queryClient.invalidateQueries(['executions'])
```

### 3. SSO Login Flow

```
1. User navigates to / or any (dashboard) route
2. middleware.ts runs authkitMiddleware: no session → redirect to /login
3. /login page calls WorkOS AuthKit signIn() → browser redirects to WorkOS
4. WorkOS authenticates user against org's IdP (SAML/OIDC)
5. WorkOS redirects to /callback?code=<auth_code>
6. /api/auth/callback (Next.js route handler) exchanges code via WorkOS SDK
7. WorkOS returns { user, org, accessToken } — accessToken is JWT (HS256 dev / RS256 prod)
8. accessToken stored in httpOnly cookie (WorkOS AuthKit handles this)
9. Redirect to /dashboard
10. All subsequent BFF requests: middleware attaches JWT from cookie to
    Authorization: Bearer <token> header before proxying to FastAPI
11. WebSocket connection: useHelixWebSocket reads JWT from cookie on mount,
    sends as first message after connection opens (JWT handshake)
```

---

## Real-Time Architecture

### WebSocket Connection Lifecycle

```typescript
// lib/ws/useHelixWebSocket.ts

const WS_URL = `${process.env.NEXT_PUBLIC_WS_URL}/api/v1/ws?token=${jwt}`;

useWebSocket(WS_URL, {
  onOpen: () => {
    // First message: JWT auth handshake
    sendJsonMessage({ type: 'auth', token: jwt });
    wsStore.setStatus('connected');
  },
  onClose: () => wsStore.setStatus('disconnected'),
  onError: () => wsStore.setStatus('error'),
  onMessage: (event) => wsEventHandlers.dispatch(JSON.parse(event.data)),
  shouldReconnect: () => true,
  reconnectAttempts: 10,
  reconnectInterval: (attempt) => Math.min(1000 * 2 ** attempt, 30000), // exp backoff, cap 30s
  heartbeat: {
    message: JSON.stringify({ type: 'ping' }),
    returnMessage: '{"type":"pong"}',
    timeout: 60000,
    interval: 25000,
  },
});
```

The WebSocket URL embeds the JWT as a query param (`?token=`) because the browser `WebSocket` constructor does not support custom headers. FastAPI validates this token before accepting the connection. The first-message handshake pattern is used as defense-in-depth.

### WebSocket Event Types

```typescript
// types/ws.ts

type WSEvent =
  | { type: 'auth_ok'; user_id: string }
  | { type: 'auth_error'; reason: string }
  | { type: 'approval_request'; approval_id: string; workflow_id: string; summary: string }
  | { type: 'workflow_status'; workflow_id: string; execution_id: string; status: ExecutionStatus }
  | { type: 'agent_activity'; workflow_id: string; agent_id: string; action: string; plain_english: string }
  | { type: 'ping' }
  | { type: 'pong' };
```

### Event → Query Invalidation

```typescript
// lib/ws/wsEventHandlers.ts

export function dispatch(event: WSEvent, queryClient: QueryClient) {
  switch (event.type) {
    case 'approval_request':
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      uiStore.getState().incrementPendingApprovals();
      break;
    case 'workflow_status':
      queryClient.invalidateQueries({ queryKey: ['executions', event.execution_id] });
      queryClient.invalidateQueries({ queryKey: ['workflows', event.workflow_id] });
      break;
    case 'agent_activity':
      queryClient.invalidateQueries({ queryKey: ['audit'] });
      break;
    case 'auth_error':
      // JWT expired mid-session — trigger re-auth
      window.location.href = '/login';
      break;
  }
}
```

### Reconnection Behavior

- Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (capped), 10 attempts total.
- After 10 failures: `wsStore.setStatus('failed')`, `WSStatusIndicator` shows red dot with "Live updates unavailable — refresh to retry."
- On reconnect: re-send JWT auth message. FastAPI re-validates. No event replay (clients re-fetch stale queries via `queryClient.invalidateQueries` on reconnect success).
- Tab visibility: pause heartbeat when `document.hidden`, resume on `visibilitychange`. Prevents battery drain on backgrounded tabs.

---

## State Management

### Division of Responsibility

| State Type | Owner | Examples |
|---|---|---|
| Server data (REST) | TanStack Query | Workflows list, approval cards, audit entries, usage stats |
| Real-time server events | WebSocket → TanStack Query invalidation | New approval arrival, execution status change |
| Persistent UI preferences | Zustand + localStorage | Sidebar collapsed, role filter selection, autonomy dial positions |
| Transient UI state | Zustand (in-memory) | Modal open, notification drawer, WS connection status |
| Canvas/editor draft | Zustand (in-memory) | Unsaved workflow nodes, NL input text, selected node |
| Auth session | WorkOS AuthKit (httpOnly cookie) | JWT, user, org_id |

### TanStack Query Configuration

```typescript
// app/layout.tsx

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // REST data fresh for 30s
      gcTime: 5 * 60_000,      // Keep unused data for 5 minutes
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
});
```

Query keys follow a hierarchical convention:
- `['workflows']` — all workflows for org
- `['workflows', id]` — single workflow
- `['approvals']` — pending approvals
- `['audit', { page, filters }]` — paginated audit log
- `['usage', { period }]` — billing/usage stats

### Zustand Stores

```typescript
// lib/store/uiStore.ts
interface UIStore {
  sidebarCollapsed: boolean;
  pendingApprovalCount: number;
  activeModal: string | null;
  notificationDrawerOpen: boolean;
  toggleSidebar: () => void;
  incrementPendingApprovals: () => void;
  setActiveModal: (id: string | null) => void;
}

// lib/store/workflowStore.ts
interface WorkflowStore {
  draftWorkflow: WorkflowDraft | null;
  selectedNodeId: string | null;
  unsavedChanges: boolean;
  nlInput: string;
  setDraft: (draft: WorkflowDraft) => void;
  updateNode: (nodeId: string, data: Partial<NodeData>) => void;
  clearDraft: () => void;
}

// lib/store/wsStore.ts
interface WSStore {
  status: 'connecting' | 'connected' | 'disconnected' | 'error' | 'failed';
  lastEventAt: Date | null;
  setStatus: (status: WSStore['status']) => void;
}
```

---

## Key Architecture Decisions

**1. BFF proxy via Next.js API routes, not direct browser-to-FastAPI REST.**
Keeps the FastAPI URL internal to the cluster. JWTs are in httpOnly cookies managed by WorkOS AuthKit — they never touch client-side JavaScript for REST calls. The BFF strips/attaches the Authorization header server-side. Direct WebSocket is the only exception, because Next.js API routes cannot proxy persistent WebSocket connections.

**2. WebSocket goes browser-direct to FastAPI, not through Next.js.**
Next.js on-demand serverless handlers cannot hold persistent TCP connections. A dedicated Kubernetes ingress rule routes `wss://api.helix.internal/api/v1/ws` with `nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"` and WebSocket upgrade headers. The JWT query param (`?token=`) is the only viable auth method because the browser WebSocket API does not support custom headers.

**3. TanStack Query for server state, Zustand for client state — no Redux.**
TanStack Query eliminates boilerplate for caching, background refresh, optimistic updates, and pagination. Zustand handles UI state that has no server representation (canvas editor, sidebar, WS status). The two libraries are purpose-built for their respective domains. Redux would add ~400 lines of boilerplate with no benefit.

**4. shadcn/ui over MUI or Ant Design.**
shadcn/ui components are copied into the codebase, not imported as a dependency. This means no version lock-in, no CSS specificity battles, and full control over accessibility. Non-technical enterprise users need clean, uncluttered UI — MUI/Ant Design's density is inappropriate for the target audience.

**5. WorkOS AuthKit for SSO, with Keycloak documented as air-gap fallback.**
WorkOS is free to 1M MAU and $125/SSO connection/month — cost-appropriate for enterprise sales. `authkitMiddleware` integrates with Next.js middleware in <50 lines. Keycloak self-hosted is the documented alternative for customers with zero-external-network requirements; the auth abstraction in `lib/auth/workos.ts` is the single swap point.

**6. React Flow (@xyflow/react v12) for the workflow canvas.**
Industry-standard library for node/edge graphs in React. MIT-licensed core. Dagre layout algorithm handles auto-positioning of AI-generated workflows. The alternative (D3 custom) would require 10x the implementation time with no UX benefit. Non-technical users interact with the canvas only to verify and lightly edit AI-generated workflows — not to build from scratch.

**7. WebSocket event invalidation rather than event-driven state updates.**
When a WebSocket event arrives, the handler calls `queryClient.invalidateQueries` to trigger a re-fetch rather than manually updating the cache from event payload. This avoids cache divergence bugs where the WS payload schema differs from the REST response schema. The extra round-trip is acceptable given the data sizes involved.

**8. Optimistic updates on approval actions, restore on failure.**
Approval cards are removed from the UI immediately on approve/reject. If the API call fails, the card is restored and an error toast explains what happened. This makes the UI feel instant for the primary workflow (approving legitimate requests) while handling the rare failure case gracefully.

**9. Multi-pod Next.js requires shared cache via Redis.**
Running multiple Next.js pods without shared cache causes each pod to diverge (different cached pages, different ISR state). `@neshca/cache-handler` backed by the same Redis instance used by FastAPI is the solution. This is a deployment requirement, not an application code concern — documented in `docker-compose.yml` and the Kubernetes Helm chart.

**10. Templates as static JSON, not database records, at launch.**
The 20+ workflow templates at launch are static JSON in `lib/api/templates.ts`, rendered client-side. This eliminates a CMS dependency and allows templates to ship with the frontend build. When the template library exceeds ~100 entries or requires per-org customization, migrating to a `GET /api/v1/templates` endpoint is the documented upgrade path.

---

## Environment Variables

```bash
# frontend/.env.example

# WorkOS AuthKit
WORKOS_API_KEY=sk_...                         # Server-side only (BFF). Never expose to browser.
WORKOS_CLIENT_ID=client_...                   # Server-side only.
WORKOS_REDIRECT_URI=https://app.helix.io/callback  # Must match WorkOS dashboard config.
WORKOS_COOKIE_PASSWORD=...                    # 32+ char random string for session cookie encryption.

# FastAPI backend (server-side, BFF use only)
FASTAPI_BASE_URL=http://helix-api-service:8000  # Internal K8s service URL. Not exposed to browser.

# WebSocket (browser-side — NEXT_PUBLIC_ prefix)
NEXT_PUBLIC_WS_URL=wss://api.helix.io          # Direct FastAPI WebSocket URL. Must use wss:// in prod.

# App config
NEXT_PUBLIC_APP_URL=https://app.helix.io       # Used for OAuth redirect construction and CSP headers.
NEXT_PUBLIC_ENVIRONMENT=production             # Values: development | staging | production

# Observability (server-side)
SENTRY_DSN=https://...@sentry.io/...           # Error tracking. Optional in dev.
SENTRY_AUTH_TOKEN=...                          # For source map upload at build time.
NEXT_PUBLIC_SENTRY_DSN=https://...             # Browser-side Sentry (separate DSN recommended).

# Redis (for multi-pod cache handler)
REDIS_URL=redis://helix-redis:6379             # Shared with FastAPI. Server-side only.

# Feature flags (optional)
NEXT_PUBLIC_ENABLE_NL_CREATOR=true             # Kill switch for NL workflow creation feature.
NEXT_PUBLIC_ENABLE_MEMORY_BROWSER=false        # Gate unreleased features per environment.
```

---

## Scaling Considerations

**What breaks first:** WebSocket connection count. Each connected browser tab holds one TCP connection to FastAPI. At 1,000 concurrent users, this is 1,000+ persistent connections. FastAPI's default Uvicorn worker count (1 per CPU) cannot handle this without `--workers N` and a connection load balancer. Solution: dedicated WebSocket service with multiple Uvicorn workers behind a sticky-session ingress rule (affinity by `session_cookie`).

**Second bottleneck:** TanStack Query re-fetch storms on WebSocket reconnect. If a network partition drops 500 connections simultaneously and they all reconnect at once, `queryClient.invalidateQueries` triggers 500 simultaneous REST fetches. Solution: jittered reconnect delay (already in exponential backoff config) plus per-query `staleTime` to suppress re-fetches for data that was recently fetched.

**Multi-tenant isolation:** `org_id` from the JWT claim is passed on every API call via the BFF. FastAPI enforces org-scoped queries. The frontend does not perform client-side org filtering — any data returned by the API is assumed to be org-correct. This keeps the trust boundary on the server side.

**Static asset CDN:** Next.js standalone build serves static assets itself. For production, put an nginx sidecar or CDN (CloudFront, Cloudflare) in front to offload static file serving. The K8s ingress should route `/_next/static/*` and `/public/*` to the CDN, all other traffic to the Next.js pod.
