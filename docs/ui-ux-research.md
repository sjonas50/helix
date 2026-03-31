# Research: Helix UI/UX for Non-Technical Enterprise Users

**Date:** 2026-03-31

## Executive Summary

Trust is the product, not the AI capability. Non-technical enterprise users (sales ops, HR, finance, CS) will adopt Helix only if they can see what agents intend to do before they do it, modify plans without starting over, and feel a visible progression from supervised to autonomous. The winning UX pattern is **natural-language-first creation → visual canvas verification → approval cards in Slack/Teams → autonomy dial that graduates over time**. The recommended frontend stack is **Next.js 15 + shadcn/ui + React Flow + TanStack Query**, self-hosted on Kubernetes (Vercel is eliminated by on-prem requirements).

---

## Problem Statement

Enterprise non-technical users need to create, monitor, and override AI agent workflows. They are not developers. They think in business outcomes, not logic gates. Their tolerance for "black box" behavior is near zero — one unexpected action erases weeks of trust. 78% of executives distrust their AI systems' decisions (S&P Global 2025). 42% of enterprise AI initiatives were abandoned in 2025, with failed user adoption as the second leading cause.

---

## The 5 UX Patterns That Win Enterprise Adoption

### 1. Natural Language → Visual Workflow (Two-Phase Builder)

User describes intent in plain English. Platform generates a visual workflow. User verifies and edits the visual representation — they never write logic directly.

**Why:** Language model handles intent→logic translation. Visual canvas gives something concrete to verify. Neither alone is sufficient — NL without visualization is unauditable; visual-only without NL is too intimidating for first-time users.

**Reference:** Zapier AI Copilot (describe → build → confirm), Make.com ("mind map" canvas), Relevance AI "Invent"

**Critical:** When the AI can't confidently map intent to steps, it must ask clarifying questions, not silently guess. Silent guessing is the leading trust-killer.

### 2. Approval Cards as First-Class Feature (HITL)

High-stakes actions pause and surface as structured interactive cards — not emails — with full context: proposed action, trigger, reasoning, and one-tap approve/reject/**modify**.

**Three options, not two:** Approve / Reject / Modify. "Modify" opens inline edit. Binary approve/reject forces users to rubber-stamp uncertainty or start over. Both are bad.

**Card must show:** What agent wants to do, why, what happens if approved, what happens if rejected, time limit, confidence signal.

**Delivery:** Slack/Teams native interactive cards via webhook. Mobile approval in under 10 seconds. A portal-only approval flow has 60-80% abandonment.

**Reference:** Moveworks (acquired by ServiceNow, $2.85B), HumanLayer (OSS), AWS Bedrock Agents HITL

### 3. The Autonomy Dial (Per-Workflow Trust Levels)

Every workflow has a 4-position dial:
1. **Observe & Suggest** — agent recommends, human acts
2. **Plan & Propose** — agent plans, shows before acting
3. **Act with Confirmation** — agent acts, human confirms
4. **Act Autonomously** — agent acts independently

Users start at position 2. After 5 consecutive approvals, platform suggests moving to position 3. The dial is always visible in the workflow header.

**Why:** Externalizes implicit trust. Maps to how trust actually develops. In error states, users move left instead of abandoning the tool entirely.

### 4. Plain-English Audit Trail with Undo

Chronological log of every agent action in business language. Each entry: what happened, when, why, and whether it's reversible. Reversible actions have an Undo button with countdown.

**Not this:** `Pipeline execution error: HTTP 429 rate_limit_exceeded`
**This:** "The email didn't send because Gmail disconnected. Click here to reconnect."

**Escalation events highlighted as positive trust signals** — evidence the agent is working as designed by asking for help when uncertain.

### 5. Template-First Onboarding (Not Blank Canvas)

New users pick from a role-organized gallery ("Sales Ops," "HR," "Finance"), not a blank canvas. Setup uses "fill in the blank" prompts. Target: first workflow live in under 10 minutes.

**Onboarding flow:**
1. Role selection → gates template gallery to relevant content
2. Template gallery (6-8 per role) with plain-English descriptions + setup time estimates
3. "Fill in the blanks" config — connect apps via OAuth, answer 3-5 questions
4. Sandbox test run — "show me what would have happened" with test data
5. Go live at autonomy position 2 (confirm everything)

---

## Common UX Mistakes That Kill Adoption

| Mistake | Why It Kills | Fix |
|---|---|---|
| Blank canvas first experience | Signals "expertise required" | Template-first with role gating |
| Silent agent actions | Correct silent action builds distrust as fast as incorrect | Action audit trail, always visible |
| Binary approve/reject only | Forces rubber-stamping or restarting | Add Modify as third option |
| Opaque usage-based pricing | Users avoid building if they can't estimate cost | Inline cost estimator |
| Technical error messages | Stack traces destroy trust | Plain-English with next-step action |
| One interface for all users | Builder ≠ approver ≠ auditor | Role-specific views |
| Over-automation in onboarding | Users need authorship over what they deploy | Guided fork, not pre-configured |

---

## Mobile Strategy

**Must work on mobile:**
- Approval cards (primary use case — approve in <10 seconds via Slack/Teams mobile)
- Push notifications with inline actions ("Reconnect Gmail")
- Read-only agent activity feed ("What did my agents do today?")

**Do NOT attempt on mobile:**
- Workflow building or canvas editing (breaks on small screens)
- Integration configuration or agent setup

---

## Recommended Frontend Stack

| Layer | Technology | Why |
|---|---|---|
| **Framework** | Next.js 15 (standalone) | Self-hosted on K8s, SSR for SEO-less enterprise app, API routes as BFF proxy |
| **Components** | shadcn/ui + Radix primitives | Own the code (copy, not dependency), WCAG 2.1 AA built-in, Tailwind CSS |
| **Workflow Canvas** | React Flow (@xyflow/react v12) | Industry standard, MIT core, AI workflow template available, dagre for layout |
| **State** | TanStack Query v5 + Zustand v5 | Server state (REST cache) + client state (UI). Replaces Redux |
| **Real-time** | WebSocket via react-use-websocket v4 | Bidirectional (approvals need send + receive). First-message JWT auth handshake |
| **Auth** | WorkOS AuthKit (free to 1M MAU) | Enterprise SSO $125/connection/month. Keycloak fallback for air-gapped |
| **Tables** | TanStack Table v8 | Audit trail, billing, workflow lists at scale |
| **Charts** | Tremor v3 or Recharts v2 | Token usage, cost attribution dashboards |
| **Forms** | React Hook Form + Zod | Workflow config, template fill-in-the-blank |
| **Testing** | Vitest 2 + Playwright 1.44 + MSW 2 | Unit/component/E2E. Drop Jest |
| **Observability** | Sentry (self-hosted or GlitchTip) | Error tracking + performance |

**Eliminated:**
- **Vercel** — $45K+/year, cloud-only, no on-prem, kills WebSocket on serverless
- **Retool/Appsmith** — internal ops only, not customer-facing product
- **Ant Design** — design signature hard to escape, dense for non-technical users
- **Redux** — replaced by TanStack Query + Zustand for 90% of use cases

---

## Architecture: Frontend ↔ Backend

```
Browser
  │
  ├─ HTTPS ──→ Next.js 15 (standalone, K8s)
  │               ├─ /api/proxy/* ──→ FastAPI REST (BFF pattern)
  │               ├─ React pages (SSR/CSR)
  │               └─ Static assets
  │
  └─ WSS ───→ FastAPI WebSocket (direct, separate ingress rule)
                ├─ First-message JWT auth handshake
                ├─ Approval notifications (push)
                ├─ Workflow status updates (push)
                └─ Approve/reject actions (client → server)
```

**Critical deployment notes:**
- WebSocket goes directly to FastAPI (Next.js cannot proxy persistent WS)
- Kubernetes ingress: separate rule for `/ws/` with `proxy-read-timeout: 3600` and upgrade headers
- Multi-pod Next.js: requires `@neshca/cache-handler` backed by Redis (pods diverge without shared cache)
- CORS: `CORSMiddleware` must be registered **before** auth middleware in FastAPI (auth 401 before CORS headers = opaque browser error)
- WebSocket JWT auth: first-message handshake pattern (browser `WebSocket` constructor ignores `Authorization` header)

---

## Key Screens to Build

| Screen | Primary User | Core Interaction |
|---|---|---|
| **Workflow Gallery** | Builder (ops specialist) | Browse templates by role, fork + customize |
| **NL Workflow Creator** | Builder | Type intent → AI generates → visual preview → edit → deploy |
| **Workflow Canvas** | Builder | React Flow visual editor, node config panels, test run |
| **Dashboard** | All | Agent activity feed, active workflows, pending approvals count |
| **Approval Queue** | Approver (manager) | Card list with context, one-tap approve/modify/reject |
| **Agent Activity Log** | Auditor / manager | Plain-English chronological log, search, filter, undo |
| **Memory Browser** | Builder / auditor | Semantic search over institutional memory, topic browse |
| **Integrations** | Builder / admin | OAuth connection flows, tool discovery, risk level display |
| **Settings / Autonomy** | Admin | Per-workflow autonomy dial, RBAC, billing/usage |
| **Token Usage** | Admin / finance | Cost attribution per org/workflow/agent, trend charts |

---

## Open Questions

1. **WorkOS vs Keycloak** — Do any target customers require zero external-network SSO broker traffic? Architecture fork, not refactor.
2. **Approval card delivery** — Slack + Teams + email + web portal? Which channels at launch?
3. **Template count at launch** — Minimum 20 templates across 4 personas. Who writes them?
4. **NL → workflow translation** — Which model? Sonnet for quality or Haiku for speed? Hybrid?
5. **Mobile app or mobile web?** — Slack/Teams cards handle 80% of mobile use. Is a native app worth the investment?
6. **Confidence signal granularity** — Per workflow, per action, or per field?
7. **Multi-tenant frontend** — Subdomain per org (`acme.helix.app`) or path-based (`app.helix.com/acme`)?

---

## Sources

- [Designing For Agentic AI: Practical UX Patterns — Smashing Magazine](https://www.smashingmagazine.com/2026/02/designing-agentic-ai-practical-ux-patterns/)
- [UX Design for Agents — Microsoft Design](https://microsoft.design/articles/ux-design-for-agents/)
- [Human-in-the-Loop UX — AufaitUX](https://www.aufaitux.com/blog/human-in-the-loop-ux/)
- [Human-in-the-Loop Approval Framework — Agentic Patterns](https://agentic-patterns.com/patterns/human-in-loop-approval-framework/)
- [Designing AI UIs That Foster Trust — UXmatters](https://www.uxmatters.com/mt/archives/2025/04/designing-ai-user-interfaces-that-foster-trust-and-transparency.php)
- [Zapier Visual Editor](https://zapier.com/blog/introducing-visual-editor/)
- [n8n vs Make 2026 — Hatchworks](https://hatchworks.com/blog/ai-agents/n8n-vs-make/)
- [Moveworks Approval Workflow](https://www.moveworks.com/us/en/platform/approval-workflow)
- [React Flow AI Workflow Editor Template](https://reactflow.dev/ui/templates/ai-workflow-editor)
- [WorkOS AuthKit React SDK](https://workos.com/docs/sdks/authkit-react)
- [WorkOS Pricing](https://workos.com/pricing)
- [Next.js Self-Hosting Docs](https://nextjs.org/docs/app/guides/self-hosting)
- [Next.js on Kubernetes — Deni Bertovic](https://denibertovic.com/posts/deploying-nextjs-to-kubernetes-a-practical-guide-with-a-complete-devops-pipeline/)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [WebSocket JWT Auth — Linode](https://www.linode.com/docs/guides/authenticating-over-websockets-with-jwt/)
- [shadcn/ui vs MUI vs Ant Design 2026 — AdminLTE](https://adminlte.io/blog/shadcn-ui-vs-mui-vs-ant-design/)
- [Retool vs Appsmith 2026 — DesignRevision](https://designrevision.com/blog/retool-vs-appsmith)
- [Vitest vs Jest vs Playwright — DevToolReviews](https://www.devtoolreviews.com/reviews/vitest-vs-jest-vs-playwright-2026-comparison)
- [S&P Global AI Adoption Survey 2025](https://www.stack-ai.com/blog/the-biggest-ai-adoption-challenges)
- [Relevance AI Reviews — G2](https://www.g2.com/products/relevance-ai/reviews)
