# Build Plan: Helix Frontend

**Date:** 2026-03-31
**Architecture:** See `docs/frontend-architecture.md`
**Total Phases:** 7 | **Estimated Tasks:** 35

---

## Phase 0: Scaffold
**Goal:** Next.js 15 project, shadcn/ui, TypeScript, Tailwind, linting, Docker-ready.
**Complexity:** S

### Tasks
1. Initialize Next.js 15 in `frontend/` with App Router, TypeScript, Tailwind CSS, ESLint
   ```bash
   npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir=false
   ```
2. Install core dependencies:
   - `@tanstack/react-query`, `zustand`, `react-use-websocket`
   - `react-hook-form`, `zod`, `@hookform/resolvers`
   - `@xyflow/react`, `dagre`
   - `lucide-react` (icons)
3. Initialize shadcn/ui: `npx shadcn@latest init` then add core components:
   - Button, Card, Dialog, Sheet, Badge, Input, Label, Select, Tabs, Table, Tooltip, DropdownMenu, Avatar, Separator
4. Create directory structure from architecture doc:
   - `app/(auth)/`, `app/(dashboard)/`, `components/{ui,workflow,approval,memory,shared}/`, `lib/{api,ws,auth,store}/`, `types/`
5. Create `next.config.ts` with `output: 'standalone'`, rewrites for `/api/proxy/*` → FastAPI
6. Create `types/api.ts` — TypeScript interfaces matching backend Pydantic schemas (Workflow, Agent, Approval, Memory, Integration, AuditEvent, Org, User)
7. Create `Dockerfile` (multi-stage: deps → build → standalone runner) and `frontend/docker-compose.yml`
8. Configure Vitest: `vitest.config.ts` + first passing test

### Test Gate
```bash
cd frontend && npm run lint && npm run build && npx vitest run
```

---

## Phase 1: Auth & Layout Shell
**Goal:** WorkOS SSO login, JWT session, protected routes, app shell (sidebar, header).
**Complexity:** M

### Tasks
1. Create `lib/auth/workos.ts` — WorkOS AuthKit server-side config + `authkitMiddleware`
2. Create `middleware.ts` — Next.js middleware: protect `(dashboard)` routes, redirect unauthenticated to `/login`
3. Create `app/(auth)/login/page.tsx` — WorkOS SSO redirect trigger (org selection → redirect to IdP)
4. Create `app/(auth)/callback/page.tsx` — Code exchange handler, set JWT cookie, redirect to dashboard
5. Create `lib/auth/useAuth.ts` — Client-side hook: session, user, org_id, roles from JWT cookie
6. Create `lib/auth/guards.ts` — Route guard HOC, role-check utilities (`requireRole("admin")`)
7. Create `components/shared/AppShell.tsx` — Sidebar + header layout wrapper
8. Create `components/shared/Sidebar.tsx` — Nav links: Dashboard, Workflows, Approvals (with badge), Memory, Integrations, Audit, Settings
9. Create `components/shared/Header.tsx` — Org name, user avatar, notification bell, WS status indicator
10. Create `app/(dashboard)/layout.tsx` — Wraps children in AppShell + QueryClientProvider + WebSocket provider
11. Create `app/(dashboard)/page.tsx` — Dashboard home (placeholder cards for now)

### Test Gate
```bash
cd frontend && npm run lint && npx vitest run && npm run build
```

---

## Phase 2: API Layer & Real-Time
**Goal:** TanStack Query hooks for all backend endpoints, WebSocket connection with JWT handshake.
**Complexity:** M

### Tasks
1. Create `lib/api/client.ts` — Fetch wrapper: attaches JWT from cookie, handles 401 (redirect to login), base URL from env
2. Create API hooks (one file per resource in `lib/api/`):
   - `workflows.ts` — `useWorkflows`, `useWorkflow`, `useCreateWorkflow`
   - `approvals.ts` — `useApprovals`, `useApproveAction`, `useRejectAction`, `useModifyAction`
   - `memory.ts` — `useMemorySearch`, `useCreateMemory`
   - `integrations.ts` — `useIntegrations`, `useProviders`, `useConnectIntegration`
   - `audit.ts` — `useAuditLog`, `useUndoAction`
   - `agents.ts` — `useAgents`, `useAgentMessages`
   - `settings.ts` — `useOrgSettings`, `useUsageStats`
3. Create `lib/ws/useHelixWebSocket.ts`:
   - Connect to `wss://api-host/api/v1/ws?token=<jwt>`
   - First-message JWT auth handshake (send `{type: "auth", token}` on open)
   - Reconnection with exponential backoff (react-use-websocket handles this)
   - Parse incoming events, dispatch to handlers
4. Create `lib/ws/wsEventHandlers.ts`:
   - `approval_request` → invalidate `['approvals']` query + show toast notification
   - `workflow_status` → invalidate `['workflows', id]` query
   - `agent_activity` → invalidate `['audit']` query
5. Create Zustand stores:
   - `lib/store/uiStore.ts` — sidebar collapsed, active modal, notification drawer
   - `lib/store/wsStore.ts` — connection status, last event timestamp
6. Write tests: API client 401 handling, WebSocket event dispatch, store state transitions

### Test Gate
```bash
cd frontend && npx vitest run --coverage && npm run build
```

---

## Phase 3: Workflow Builder
**Goal:** Template gallery, NL creator, React Flow canvas editor, test run panel.
**Complexity:** L

### Tasks
1. Create `app/(dashboard)/workflows/page.tsx` — Workflow Gallery:
   - Role-filtered template cards (Sales Ops, HR, Finance, CS categories)
   - Search/filter by name, category, integration
   - "Create from scratch" and "Describe in English" CTAs
2. Create `components/workflow/NLCreator.tsx`:
   - Text input with placeholder examples per role
   - Submit → call LLM endpoint → receive workflow graph JSON
   - Loading state with progress indicator
   - Preview generated workflow on canvas before deploying
3. Create `components/workflow/Canvas.tsx`:
   - React Flow wrapper with dagre auto-layout
   - Custom node types: TriggerNode, ActionNode, ConditionNode, ApprovalNode, AgentNode
   - Edge labels showing data flow
   - Minimap + controls
4. Create custom nodes in `components/workflow/nodes/`:
   - `TriggerNode.tsx` — Event source (webhook, schedule, manual)
   - `ActionNode.tsx` — Integration tool call with risk level badge
   - `ConditionNode.tsx` — If/else branch
   - `ApprovalNode.tsx` — HITL pause point with estimated SLA
   - `AgentNode.tsx` — LLM agent with role badge
5. Create `components/workflow/NodeConfigPanel.tsx` — Slide-in sheet for selected node configuration
6. Create `components/workflow/TestRunPanel.tsx` — Sandbox execution: run with test data, show plain-English results
7. Create `components/shared/AutonomyDial.tsx` — 4-position segmented control (Suggest / Plan / Confirm / Autonomous)
8. Create `app/(dashboard)/workflows/[id]/page.tsx` — Single workflow view with canvas + config + run history

### Test Gate
```bash
cd frontend && npx vitest run && npx playwright test tests/e2e/workflow.spec.ts
```

---

## Phase 4: Approval Queue & Audit Trail
**Goal:** Real-time approval cards, 3-way decision UI, audit log with undo.
**Complexity:** M

### Tasks
1. Create `components/approval/ApprovalCard.tsx`:
   - Shows: action description, trigger reason, risk level badge, confidence signal
   - 3 buttons: Approve (green), Modify (yellow), Reject (red)
   - Time remaining countdown ("Expires in 3h 42m")
   - Expandable context section (full payload, affected records)
2. Create `components/approval/ApprovalQueue.tsx`:
   - Sorted by urgency (SLA deadline), filterable by risk level
   - Batch approve for LOW risk items
   - Real-time: new cards animate in on WebSocket event
   - Empty state: "All caught up" with confetti or checkmark
3. Create `components/approval/ModifyDrawer.tsx`:
   - Sheet slides in when user clicks "Modify"
   - Editable fields for the proposed action (pre-filled)
   - Submit modified version → agent continues with changes
4. Create `app/(dashboard)/audit/page.tsx` — Audit Trail:
   - `TanStack Table` with columns: timestamp, event, agent, workflow, resource, status
   - Plain-English event descriptions (not technical logs)
   - Filter by: date range, event type, workflow, agent
   - Undo button on reversible actions with countdown
5. Create `components/shared/AuditEntry.tsx` — Single audit row with optional undo
6. Write tests: approval card rendering, 3-way decision mutations, audit table pagination, undo flow

### Test Gate
```bash
cd frontend && npx vitest run && npx playwright test tests/e2e/approvals.spec.ts
```

---

## Phase 5: Memory, Integrations, Settings
**Goal:** Semantic search UI, integration OAuth flows, autonomy settings, billing.
**Complexity:** M

### Tasks
1. Create `app/(dashboard)/memory/page.tsx` — Memory Browser:
   - `components/memory/MemorySearch.tsx` — Semantic search input with typeahead
   - `components/memory/TopicTree.tsx` — Hierarchical topic navigation
   - `components/memory/MemoryCard.tsx` — Single entry with access level badge, version history
   - Empty state: "No memories yet — agents learn as they work"
2. Create `app/(dashboard)/integrations/page.tsx` — Integration Hub:
   - Grid of provider cards (Salesforce, Slack, Jira, etc.) with connection status
   - "Connect" button → OAuth redirect flow via Composio
   - Connected integrations: show available tools, risk levels, last sync
   - "Disconnect" with confirmation dialog
3. Create `app/(dashboard)/settings/page.tsx` — Org Settings:
   - General: org name, plan, timezone
   - `settings/autonomy/page.tsx` — Per-workflow autonomy dial management (table of workflows × dial)
   - `settings/members/page.tsx` — RBAC: invite users, assign roles, remove
   - `settings/billing/page.tsx` — Token usage charts (Tremor/Recharts), cost attribution per workflow/agent, spend trend
4. Write tests: memory search, integration connect flow, autonomy dial state, billing chart rendering

### Test Gate
```bash
cd frontend && npx vitest run && npm run build
```

---

## Phase 6: Hardening & Deployment
**Goal:** Playwright E2E suite, Docker, Kubernetes-ready, error boundaries, loading states.
**Complexity:** M

### Tasks
1. Create `components/shared/ErrorBoundary.tsx` — Plain-English error fallback (never show stack traces)
2. Add loading skeletons to all pages (shadcn/ui Skeleton component)
3. Create Playwright E2E tests in `tests/e2e/`:
   - `login.spec.ts` — SSO redirect flow (mock WorkOS)
   - `workflow.spec.ts` — Create from template → deploy → verify on canvas
   - `approvals.spec.ts` — Receive approval → approve/reject/modify → verify state
   - `memory.spec.ts` — Semantic search → results → view detail
4. Finalize `frontend/Dockerfile`:
   ```dockerfile
   FROM node:20-alpine AS deps
   # install dependencies
   FROM node:20-alpine AS builder
   # build standalone
   FROM node:20-alpine AS runner
   # copy .next/standalone + public + static
   ```
5. Add frontend service to root `docker-compose.yml`:
   ```yaml
   frontend:
     build: ./frontend
     ports: ["3000:3000"]
     environment:
       - NEXT_PUBLIC_API_URL=http://api:8000
       - NEXT_PUBLIC_WS_URL=ws://api:8000
   ```
6. Add frontend to Helm chart: Deployment, Service, Ingress path routing (`/` → frontend, `/api/*` → FastAPI, `/ws/*` → FastAPI)

### Test Gate
```bash
cd frontend && npm run lint && npx vitest run && npx playwright test && npm run build
```

---

## Phase Summary

| Phase | Name | Tasks | Complexity | Key Deliverable |
|---|---|---|---|---|
| 0 | Scaffold | 8 | S | Next.js 15 + shadcn/ui + types + Docker |
| 1 | Auth & Layout | 11 | M | WorkOS SSO, protected routes, app shell |
| 2 | API & Real-Time | 6 | M | TanStack Query hooks, WebSocket + event dispatch |
| 3 | Workflow Builder | 8 | L | NL creator, React Flow canvas, template gallery |
| 4 | Approvals & Audit | 6 | M | 3-way approval cards, plain-English audit with undo |
| 5 | Memory + Settings | 4 | M | Semantic search, integrations, autonomy dial, billing |
| 6 | Hardening | 6 | M | E2E tests, Docker, Helm, error boundaries |

**Critical path:** Phase 0 → Phase 1 → Phase 2 → (Phase 3 + Phase 4 in parallel) → Phase 5 → Phase 6

Phases 3 (workflow builder) and 4 (approvals + audit) can be built in parallel since they share the API layer from Phase 2 but don't depend on each other.
