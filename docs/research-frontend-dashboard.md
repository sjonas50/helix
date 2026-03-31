# Research: Frontend Framework for Enterprise AI Agent Orchestration Dashboard

## Executive Summary

The target users (sales ops, finance, HR, CS managers) need a polished, no-code-feeling product UI — not an internal tool. That rules out Retool/Appsmith as the primary choice, though they are valid for rapid internal prototyping. The recommended stack is **Next.js 15 (App Router) + shadcn/ui + TanStack Table/Query + React Flow** — it delivers enterprise-grade UX, WCAG 2.1 AA accessibility, full real-time capability via SSE/WebSocket, and full brand control. This is the only approach that can be sold as a product rather than exposed as scaffolding.

---

## Problem Statement

Build a frontend for a multi-persona enterprise SaaS dashboard where non-technical users (sales ops, finance, HR, CS) need to: configure and trigger AI agent workflows without writing code; monitor real-time workflow progress; manage approval queues; search institutional memory; connect SaaS OAuth integrations; and review audit trails with token/billing visibility.

Requirements that constrain the choice:
- Sold as a **product** (white-label quality, not "built with Retool")
- Non-technical end users — UX must be exceptional, not developer-friendly
- Real-time updates: agent activity streams, approval queues, live logs
- Complex UI surfaces: node-based workflow canvas, data tables, approval flows
- Enterprise procurement: SSO, RBAC, audit logs, SOC 2 readiness
- Velocity matters: team needs a productive full-stack pattern now

---

## Technology Evaluation

### Comparison Matrix

| Approach | Maturity | Enterprise UX | Real-Time | Component Quality | Accessibility | Mobile | Learning Curve | Community | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Next.js 15 + shadcn/ui** | High (stable, LTS) | Excellent (full control) | Yes (SSE + WS, non-serverless req.) | Excellent (Radix primitives) | WCAG 2.1 AA OOB | Good | Medium | 88k+ stars (shadcn) | **RECOMMENDED** |
| **Refine.dev + shadcn/ui** | Medium-High (v4, active) | Good (opinionated CRUD) | Yes (via adapters) | Good (composable) | Inherits shadcn | Good | Low-Medium | 29k stars | **Consider** |
| **Ant Design Pro (v6)** | Very High (Alibaba) | Good (dense, enterprise) | Yes | Excellent (60+ components) | WCAG 2.1 partial | Limited | Low (AntD v6 breaking) | 91k stars | **Consider** |
| **Retool / Appsmith** | High (Retool) / Medium (Appsmith) | Poor for products | Yes (built-in) | Low (visual builder) | Limited | Poor | Very Low | Proprietary | **Avoid (product)** |
| **Vite SPA + shadcn/ui** | High (Vite 6) | Excellent (full control) | Yes | Excellent | WCAG 2.1 AA | Good | Low | Very large | **Consider (alt)** |

---

### Option A: Next.js 15 + shadcn/ui + TanStack + React Flow — RECOMMENDED

**Versions:** Next.js 15.x, shadcn/ui (registry-based, no version pin), TanStack Table v8, TanStack Query v5, React Flow (@xyflow/react v12)

**Why it wins for this use case:**
- shadcn/ui is not a package — it's copied source code with Radix UI primitives. You own every component. No upstream breaking changes blow up production.
- WCAG 2.1 AA compliance is built into Radix primitives (focus management, ARIA, keyboard nav). Critical for enterprise procurement.
- Next.js App Router with React Server Components gives you SSR for the marketing/login shell and full client interactivity for the dashboard — clean separation.
- SSE (Server-Sent Events) via Next.js Route Handlers is the right pattern for agent activity streams. Native `ReadableStream` API, works without WebSocket servers.
- TanStack Table v8: headless, virtualized, supports sorting/filtering/grouping/pagination at 100k+ rows. The only choice for audit trail and billing tables.
- React Flow (@xyflow/react v12) is the de facto standard for node-based workflow canvas (used by Stripe, Typeform). Ships with a ready-made AI Workflow Editor template built on shadcn/ui as of 2025.

**Deployment constraint:** WebSockets require Node-based deployment (Railway, Render, fly.io, self-hosted). Do NOT deploy to Vercel serverless if you need persistent WebSocket connections. SSE works on Vercel with caution (60s timeout on hobby plans; fine on enterprise plans).

**Gotchas:**
- Next.js App Router is still maturing. Server/client component boundary errors are the #1 DX complaint in 2025.
- shadcn/ui registry model means manual component updates — not `npm update`. Requires discipline.
- React Flow Pro subscription ($x/month) needed for priority support; open-source license (MIT) is free.

---

### Option B: Refine.dev (v4) + shadcn/ui — Consider

**Version:** Refine 4.x, open source (MIT)

Refine is a React meta-framework purpose-built for admin panels and internal tools. It wires up data providers, auth providers, access control (RBAC/ABAC), routing, and CRUD state management so you don't write boilerplate. It integrates with shadcn/ui as a UI layer.

**Use it when:** Team is small, velocity is paramount, and the product is closer to "internal tool with polish" than "consumer SaaS." Refine reduces 60-70% of CRUD scaffolding but constrains architecture.

**Avoid it when:** The product needs heavy custom UX beyond CRUD (workflow canvas, semantic search, real-time approval queues). You hit Refine's abstractions and fight them.

---

### Option C: Ant Design Pro v6 — Consider

**Version:** Ant Design 6.0 (React 18+, CSS variables default, drops Less, drops IE)

Ant Design is Alibaba's battle-hardened enterprise component library with 60+ components including the richest free data-dense components (Table, Tree, Transfer, Cascader, Form). ProComponents adds ProTable (extremely powerful), ProForm, and ProLayout.

**Use it when:** The team already knows AntD, the product targets Chinese enterprise market, or data density matters more than brand differentiation.

**Avoid it when:** Design uniqueness is a sales differentiator. AntD apps look like AntD apps — very hard to escape the visual signature. v6 migration is non-trivial (Less → CSS tokens, DOM restructuring, React 19 prep).

---

### Option D: Retool / Appsmith / ToolJet — AVOID for product

**Retool pricing (2025):** $65/standard user/month, $18/end user/month. Enterprise (50 standard + 200 end users) = $94k–$204k/year negotiated. Workflow runs sold in packs of 50k/month.

**The fundamental problem:** These platforms are for building internal tools fast, not for selling a SaaS product. End users see "Built with Retool" infrastructure. You can't white-label the runtime fully. When you sell to enterprises, procurement will reject vendor-in-vendor risk. Custom domains and white-labeling are Enterprise-tier only.

**One legitimate use:** Build an internal admin panel for your own ops team (NOT what end-users see) using Retool/Appsmith. Fast, cheap, maintainable by non-engineers.

---

### Option E: Vite SPA + shadcn/ui — Consider (Simpler Alternative)

**Versions:** Vite 6.x, React 19

If the team doesn't need SSR, Vite + React is simpler than Next.js. No server/client component boundary confusion. Smaller bundles (42KB vs 92KB baseline). Faster dev server. All real-time patterns work identically.

**Use it when:** The whole app is behind auth (no SEO needed), team is unfamiliar with Next.js App Router nuances, or deployment target is a Docker container / CDN with separate API.

---

## Architecture Patterns Found

**Pattern 1: Dashboard Shell + Workflow Canvas + Table Grid**
- Shell: Next.js App Router layout with sidebar nav (shadcn/ui `Sheet`, `NavigationMenu`)
- Canvas: React Flow with custom nodes for agent types, edge labels for data flow
- Tables: TanStack Table v8 with virtualization for audit logs / billing
- Real-time: SSE via Next.js Route Handlers (`/api/agent-stream`) → client `EventSource`

**Pattern 2: Approval Queue**
- Approval items as cards in a Kanban column (shadcn/ui `Card` + DnD)
- Optimistic mutation via TanStack Query `useMutation` with rollback
- WebSocket push to notify pending approvers (requires Node server, not serverless)

**Pattern 3: OAuth Integration Gallery**
- Each connector as a card with status badge
- OAuth flow: redirect → callback → token exchange via Next.js Route Handler
- Store tokens encrypted server-side; never expose to client

**Pattern 4: Semantic Memory Search**
- Search bar with debounced queries → vector DB API (Pinecone/pgvector)
- Results as `Command` palette (shadcn/ui `cmdk`) — familiar UX pattern for power users

**Reference implementations:**
- Tersa (open source AI workflow canvas): uses React Flow + shadcn/ui
- React Flow AI Workflow Editor Template: ships with shadcn/ui nodes, auto-layout
- Waldiez: multi-agent visual orchestration on React Flow

---

## Key APIs and Services

| Service | Purpose | Auth | Rate Limits / Pricing |
|---|---|---|---|
| React Flow Pro | Priority support, enterprise license | Subscription | $x/mo (open source is free/MIT) |
| TanStack (all) | Open source | None | Free, MIT |
| shadcn/ui | Component registry | None | Free, MIT |
| Vercel (Next.js hosting) | Deployment | API key | SSE: 60s timeout (hobby), unlimited (enterprise). WS: not supported serverless |
| Pusher / Ably | Managed WebSocket | API key | Pusher: 200 connections free, $49/mo+ enterprise |
| PartyKit | Edge WebSocket | API key | Usage-based, ~$0.05/GB |

---

## Known Pitfalls and Risks

1. **Next.js App Router "use client" hell.** React Flow and all interactive components require `"use client"`. Next.js Server Components cannot import client components without a boundary. This bites teams new to App Router. Mitigation: Vite avoids this entirely.

2. **WebSocket on serverless = broken.** Vercel Edge/Lambda kills connections after 60s. If you need live agent progress streams, either use SSE (works on Vercel with enterprise limits) or run a stateful Node server alongside.

3. **React Flow performance at scale.** Large graphs (500+ nodes) need virtualization. React Flow handles this with `useNodesInitialized` + viewport culling, but requires deliberate optimization.

4. **Ant Design v6 migration risk.** v5 enters maintenance mode (1-year window). If you start on v5, you will pay the migration cost to v6 (Less → CSS tokens, DOM structure changes, React 18 requirement). Start on v6 directly.

5. **shadcn/ui is not a package.** No `npm update` path. Component updates require manual review/merge of generated diffs. At scale (50+ components), this requires a governance process. shadcn Registry 2.0 (2025) adds private registries and compliance checks to address this.

6. **Retool lock-in.** If you build on Retool and later want to migrate, you rewrite everything. The YAML/JSON app definitions are not portable. Start product-quality work on a real framework from day one.

7. **TanStack DB (v0.5, new in 2025).** Promising real-time sync layer for TanStack Query but still pre-1.0. Do not use in production yet for the billing/audit features — use TanStack Query v5 with standard polling or SSE instead.

---

## Recommended Stack

**For a team building an enterprise AI agent orchestration product sold to non-technical users:**

```
Framework:       Next.js 15 (App Router, Node deployment — NOT serverless)
UI Library:      shadcn/ui (Radix primitives, Tailwind CSS 4)
Data Tables:     TanStack Table v8 + TanStack Query v5
Workflow Canvas: @xyflow/react v12 (React Flow)
Real-time:       Server-Sent Events via Next.js Route Handlers (agent streams)
                 Pusher or Ably for bi-directional (approval notifications)
Forms:           React Hook Form v7 + Zod v3 (integrates with shadcn Form)
State:           TanStack Query (server state) + Zustand v5 (UI state)
Auth:            NextAuth.js v5 (Auth.js) — handles OAuth + session
Charts:          Recharts v2 or Tremor v3 (built on Recharts + Tailwind)
Search/Command:  cmdk v1 (ships with shadcn/ui)
Deployment:      Railway or fly.io (Node persistent), NOT Vercel serverless
```

**If team is small and velocity is more important than product polish:** Start with Refine.dev v4 + shadcn/ui adapter. You can migrate the UI layer later while keeping the data/auth patterns.

**For your own internal ops tooling (NOT what customers see):** Appsmith (self-hosted, free, MIT) is the right call. Fast, no maintenance overhead.

---

## Open Questions

1. Does the workflow canvas need execution (running agents) or just configuration? Execution requires a persistent backend connection — this drives the serverless vs. Node deployment decision hard.
2. What is the expected concurrent user count? This affects WebSocket vs. SSE vs. polling choice and hosting cost.
3. Is mobile support a hard requirement or a nice-to-have? React Flow canvas UX on mobile is poor. If mobile is required, the canvas needs a separate simplified view.
4. White-label / multi-tenant theming? shadcn/ui with CSS variables supports per-tenant theming natively via Tailwind config. AntD v6 supports design tokens similarly.
5. Accessibility tier required by enterprise procurement? WCAG 2.1 AA is standard. Some US federal / healthcare customers require Section 508. shadcn/ui covers both.

---

## Sources

- [27 Best React Admin Dashboard Templates 2026 — AdminLTE](https://adminlte.io/blog/react-admin-dashboard-templates/)
- [React Admin Dashboard Guide — Refine.dev](https://refine.dev/blog/react-admin-dashboard/)
- [React UI Libraries 2025: shadcn, Radix, Mantine, MUI, Chakra — Makers Den](https://makersden.io/blog/react-ui-libs-2025-comparing-shadcn-radix-mantine-mui-chakra)
- [shadcn/ui vs MUI vs Ant Design 2026 — AdminLTE](https://adminlte.io/blog/shadcn-ui-vs-mui-vs-ant-design/)
- [UI Framework Battle 2025: ShadCN vs Ant Design — Lafu Code](https://lafucode.com/en/posts/frontend-ui-frameworks-2025)
- [Retool vs Appsmith: Internal Tools Comparison 2026 — DesignRevision](https://designrevision.com/blog/retool-vs-appsmith)
- [Retool Pricing 2025 — Superblocks](https://www.superblocks.com/compare/retool-pricing-cost)
- [Retool Agents — retool.com](https://retool.com/agents)
- [10 Best Internal Tool Builders 2025 — Reflex Blog](https://reflex.dev/blog/2025-06-03-internal-tool-builders-2025/)
- [Next.js vs Remix 2025 — Strapi](https://strapi.io/blog/next-js-vs-remix-2025-developer-framework-comparison-guide)
- [Vite vs Next.js 2026 — DesignRevision](https://designrevision.com/blog/vite-vs-nextjs)
- [React Stack Patterns 2026 — patterns.dev](https://www.patterns.dev/react/react-2026/)
- [React Flow AI Workflow Editor Template — reactflow.dev](https://reactflow.dev/ui/templates/ai-workflow-editor)
- [xyflow Spring Update 2025](https://xyflow.com/blog/spring-update-2025)
- [TanStack DB 0.1 Announcement](https://tanstack.com/blog/tanstack-db-0.1-the-embedded-client-database-for-tanstack-query)
- [TanStack 2026: Full-Stack Revolution — byteiota](https://byteiota.com/tanstack-2026-full-stack-revolution-with-query-router/)
- [Build Admin Dashboard with shadcn/ui + TanStack Start — freeCodeCamp](https://www.freecodecamp.org/news/build-an-admin-dashboard-with-shadcnui-and-tanstack-start/)
- [Real-Time SSE in Next.js 15 — Damian Hodgkiss](https://damianhodgkiss.com/tutorials/real-time-updates-sse-nextjs)
- [Ant Design v5 to v6 Migration Guide](https://ant.design/docs/react/migration-v6/)
- [Accessible shadcn/ui Components Guide — BrightCoding](http://www.blog.brightcoding.dev/2025/12/15/the-ultimate-guide-to-accessible-shadcn-ui-components-build-production-ready-apps-with-react-typescript-tailwind-css)
- [Refine Framework Enterprise Overview](https://refine.dev/)
- [No-Code Workflow Automation 2026 — WeWeb](https://www.weweb.io/blog/no-code-workflow-automation-complete-guide)
