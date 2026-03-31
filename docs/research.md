# Research: Claude Code Leaked Source — Comprehensive Technical Analysis

## Executive Summary

On March 31, 2026, Anthropic accidentally shipped version 2.1.88 of `@anthropic-ai/claude-code` to npm with a 59.8 MB source map file included, exposing ~1,900 TypeScript files and 512,000+ lines of production code. This was the second such exposure (a prior incident occurred in early 2025). The codebase reveals a sophisticated multi-agent coding system far ahead of its public feature set, built on Bun + TypeScript + React/Ink, with unreleased subsystems including always-on background agents (KAIROS), memory consolidation (autoDream), speculative execution, a companion pet (BUDDY), a remote 30-minute planning mode (ULTRAPLAN), and an active anti-distillation defense system. The internal project codename is "Tengu."

---

## Problem Statement

This document answers: what is Claude Code actually doing under the hood? The leak is the most complete window into a production-grade AI coding agent ever made public. It matters for anyone building competing or complementary systems — the architecture patterns, permission models, and feature design represent 18+ months of production iteration.

---

## 1. Overall Architecture

### Tech Stack
- **Runtime**: Bun (not Node.js). Chosen for faster startup and native dead-code elimination via compile-time feature flags.
- **Language**: TypeScript throughout. ~1,900 files, 512,000+ lines.
- **UI**: React + Ink (terminal UI framework) with a custom reconciler on top of the Yoga flexbox engine.
- **Validation**: Zod v4 for all tool schemas, API response validation, and config files.
- **Feature flags**: GrowthBook (migrated from Statsig) for server-side remote configuration.
- **Analytics**: Every internal event prefixed `tengu_*` (e.g., `tengu_startup_telemetry`, `tengu_mcp_channel_flags`).

### Directory Structure (35 top-level directories)
```
assistant/       # KAIROS always-on mode
bridge/          # JWT-auth IPC for IDE integrations and claude.ai
buddy/           # Tamagotchi companion system (feature-gated)
cli/             # Entry point and CLI argument parsing
commands/        # ~50 slash commands (/commit, /review-pr, etc.)
components/      # React terminal components
coordinator/     # Multi-agent orchestration
hooks/           # Pre/post tool execution automation
ink/             # Custom React terminal renderer
memdir/          # Memory file management
remote/          # Remote execution (CCR — Claude Code Remote)
schemas/         # Pydantic-equivalent Zod schemas
services/        # autoDream background memory consolidation
skills/          # User-defined skill scripts
tools/           # 40+ tool implementations
upstreamproxy/   # API proxy layer
utils/           # undercover.ts, fastMode.ts, etc.
voice/           # Voice interaction (feature-gated)
```

### Entry Point
`main.tsx` at 785KB is the primary entry point. Parallelized startup fires MDM policy reads and OAuth keychain fetches concurrently before module imports complete, exploiting TypeScript evaluation latency as a performance trick.

### Execution Modes
Claude Code can run as: interactive CLI, non-interactive headless (`--print`/`-p`), MCP server, bridge (remote connection to claude.ai), local/remote agent, and coordinator. Mode detection uses `CLAUDE_CODE_ENTRYPOINT`.

---

## 2. Tool System

### Scale and Registration
- ~40-60 tools registered (sources vary between 40 and 60+ due to gated tools)
- Base tool definition (`Tool.ts`): **29,000 lines**
- Tools are sorted alphabetically in the registry specifically to maximize prompt cache hit rates — the order affects caching since the tool list appears in the system prompt

### Tool Categories
| Category | Tools |
|---|---|
| File ops | FileRead, FileEdit, FileWrite, Glob, Grep |
| Execution | Bash, PowerShell, REPL, LSP |
| Web | WebFetch, WebSearch, WebBrowser |
| Agent mgmt | AgentSpawn, TeamCreate, TeamDelete, TeammateTool |
| Task mgmt | TaskCreate, TaskGet, TaskList, TaskUpdate, TaskOutput, TaskStop |
| Scheduling | CronCreateTool, CronDeleteTool, CronListTool (KAIROS-gated) |
| Specialized | NotebookEdit, SkillInvoke, MCPResource, GitWorktree, WorkflowExec |
| KAIROS-only | SendUserFile, PushNotification, SubscribePR |
| Internal | ConfigTool, TungstenTool |

### Permission Model
Five permission modes:
- `default` — interactive prompts for every action
- `plan` — approve plan but auto-approve execution
- `acceptEdits` — auto-approve file edits
- `bypassPermissions` — skip checks entirely (internal use, `USER_TYPE=ant`)
- `dontAsk` — deny all without asking (mislabeled "YOLO" in public discourse)

Every tool action is classified LOW / MEDIUM / HIGH risk. The `classifyYoloAction()` function uses a fast Claude inference call to evaluate its own tool authorization decisions in auto-approval mode. Protected files (`.gitconfig`, `.bashrc`, `.zshrc`, `.mcp.json`, `.claude.json`) are unconditionally blocked from modification. `DISABLE_COMMAND_INJECTION_CHECK` env var bypasses the injection check entirely — a dangerous escape hatch.

Hooks system provides pre/post-execution automation with four types: `command`, `prompt`, `HTTP`, `agent`. Three-level pipeline: event → matcher → hook.

### Tool Dispatch
Tools support concurrent execution (read-only tools) and serial execution (write tools). Deferred discovery via `ToolSearchTool` for lazy loading. 18 tools are deferred to reduce binary footprint. The `Promise.race()` pattern in concurrent tool calls has a known issue: ~5.4% of tool calls are "orphaned" — results never return to context on race loss. This is a documented architectural flaw, not a bug that was fixed.

---

## 3. Query Engine

### Scale
`QueryEngine.ts`: **46,000 lines** — the largest single component and central orchestration hub.

### Core Loop
Implements a `while(true)` retry loop with resilient state machines. Handles:
- Message accumulation across multi-turn conversations
- LLM API call orchestration and streaming
- Automatic context compression when token budgets approach limits
- Circuit breaker: limits consecutive failures to 3 before surfacing error

### Streaming and Failure Modes
Three automatic silent downgrades (no user notification):
1. Server overload (529 errors) → silent model switch Opus → Sonnet
2. Streaming hang → non-streaming fallback with internal telemetry flag
3. Rate limits → exponential backoff retry

The watchdog protecting the SSE event loop is initialized *after* the initial connection phase — meaning the 100% of observed hangs happen in the unprotected window. The `AbortController` hierarchy has 5 nested levels but supports top-down cancellation only.

### Context Compression (Three Layers)
1. **Microcompaction**: Bulky tool outputs offloaded to disk early; model sees references, not data. Cache policy controls inline retention and size threshold.
2. **Auto-compaction**: Fires at ~83.5% context usage (~167K of 200K tokens). Reserves 33K tokens (16.5%) for output headroom. Structured summary: intent, decisions, affected files, errors, pending tasks, next steps. Continuation message injected post-compaction. Controllable via `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`.
3. **Manual compaction**: User-initiated via `/compact` with optional focus hints.

### System Prompt Architecture
Not a single string — built from modular cached sections at runtime:
- `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` marker splits static (cross-org cacheable) from dynamic (user/session-specific, cache-breaking) sections
- `DANGEROUS_uncachedSystemPromptSection()` function for volatile content that must not be cached
- Tool list is static and cached; user identity is dynamic

---

## 4. Multi-Agent / Coordinator System

### Coordinator Mode
Activated via `CLAUDE_CODE_COORDINATOR_MODE=1`. Orchestrator delegates to parallel workers:
- **Research phase**: Workers conduct concurrent investigations
- **Synthesis phase**: Coordinator merges findings into specs
- **Implementation phase**: Separate worker agents
- **Verification phase**: Testing agents

The system explicitly teaches against serialized work in its prompt — workers are instructed to parallelize rather than chain.

### TeammateTool (13 Operations)
The hidden swarm system, gated behind two feature gates (`I9()` and `qFB()` in the obfuscated build):

**Lifecycle**: `spawnTeam`, `discoverTeams`, `cleanup`, `requestJoin`, `approveJoin`, `rejectJoin`
**Coordination**: `write` (direct message), `broadcast` (all agents), `approvePlan`, `rejectPlan`
**Shutdown**: `requestShutdown`, `approveShutdown`, `rejectShutdown`

Agent identity controlled via env vars: `CLAUDE_CODE_TEAM_NAME`, `CLAUDE_CODE_AGENT_ID`, `CLAUDE_CODE_AGENT_TYPE`.

### Isolation
- Each agent gets its own git worktree at `.claude/worktrees/<task-id>/` on its own branch
- File-based IPC with lock files for concurrent access coordination
- Messages stored at `~/.claude/teams/{team-name}/messages/{session-id}/`
- Scratch directory sharing between coordinator and workers via `tengu_scratch` feature gate
- **Subagents cannot spawn sub-subagents** — single level of hierarchy enforced

### Isolation Modes
`AgentTool` supports two isolation modes: `worktree` (git worktree isolation) and `remote` (CCR execution).

---

## 5. Memory System (autoDream)

### Architecture Overview
Four-layer memory stack:
1. `CLAUDE.md` — static instructions you write
2. **Auto Memory** — notes Claude writes per session (captures)
3. **Session Memory** — in-context conversation continuity
4. **Auto Dream** — periodic background consolidation (organizes)

Memory files stored at `~/.claude/projects/<slug>/memory/` with YAML frontmatter. A Sonnet-powered relevance selector retrieves up to 5 most relevant files per turn without loading the full directory.

### autoDream Four Phases
autoDream runs as a **forked subagent** (not in the main process). Bash is restricted to read-only during dream execution.

**Phase 1 — Orient**: `ls` the memory directory, read `MEMORY.md` index, skim existing topic files to avoid creating duplicates.

**Phase 2 — Gather Signal**: Targeted grep of session transcripts (JSONL) for: user corrections, explicit save commands, recurring themes, significant architectural decisions. Narrow approach conserves tokens.

**Phase 3 — Consolidate**: Write/update memory files. Convert relative dates to absolute (e.g., "yesterday" → "2026-03-15"), remove contradicted facts, merge overlapping entries, prune stale references.

**Phase 4 — Prune and Index**: Maintain `MEMORY.md` under **200 lines / 25KB cap**. Remove obsolete pointers, add new files, resolve contradictions, reorder by relevance.

### Three-Gate Trigger System
All conditions must pass simultaneously:
1. **24+ hours** since last dream run
2. **5+ sessions** since last dream (prevents triggering on low-activity projects)
3. **Consolidation lock acquisition** (prevents concurrent runs on shared/team projects)

Feature gate: `tengu_onyx_plover` (currently disabled for general users, enabled via `tengu_kairos_cron` for KAIROS users).

Theoretical basis: UC Berkeley + Letta "Sleep-time Compute" paper (April 2025) showing models that pre-compute during idle time reduce test-time compute by 5x at equal accuracy with up to 18% accuracy gains. One observed benchmark: 913 sessions consolidated in under 9 minutes.

---

## 6. IDE Bridge

### Architecture
Bidirectional communication layer in `bridge/` directory connecting the CLI to IDE extensions (VS Code, JetBrains) and to claude.ai's browser interface.

**Key files**:
- `bridgeMain.ts` — main event loop
- `bridgeMessaging.ts` — protocol definition
- `bridgePermissionCallbacks.ts` — permission delegation back to IDE
- `replBridge.ts` — REPL session management
- `jwtUtils.ts` — JWT authentication
- `sessionRunner.ts` — session lifecycle

### Authentication
JWT-authenticated channels with trusted device enrollment for elevated security tiers. Token refresh is handled automatically within the bridge loop. Message adaptation layer normalizes between CLI-native and browser-based message formats.

### Work Modes
Supports `single-session`, `worktree`, and `same-dir` modes, controlling how the bridge handles file access when the IDE and CLI have different working directories.

### WebSocket Connection
The bridge maintains a WebSocket connection to claude.ai, enabling browser-based interaction (approval dialogs, permission grants) while actual tool execution happens locally in the CLI process.

---

## 7. Terminal UI

### Stack
- **React + Ink**: Component-based terminal UI identical to web React mental model
- **Custom reconciler**: Anthropic wrote a custom React reconciler on top of Ink (not using Ink's default one)
- **Yoga**: Flexbox layout engine — CSS-like box model in the terminal
- **Double-buffering**: Screen updates use a double-buffer to minimize flicker
- **Hardware scroll optimization**: Uses terminal hardware scroll regions rather than full redraws for large output
- **Three interning pools**: Characters, styles, and hyperlinks are interned for O(1) equality comparisons — avoids string comparison overhead in the render loop

### Performance
The custom reconciler avoids Ink's default behavior of full-tree traversal on every state change. Text selection, mouse events, and hardware scroll regions are all supported.

---

## 8. Unreleased Features

### KAIROS — Always-On Proactive Assistant
- Persistent background agent with append-only daily logging
- "Tick" prompts at intervals for autonomous decision-making
- 15-second blocking budget to avoid intruding on user work
- Exclusive tools: `SendUserFile`, `PushNotification`, `SubscribePRTool` (GitHub webhook integration via `KAIROS_GITHUB_WEBHOOKS` flag)
- Feature gate: `feature('KAIROS') + tengu_kairos`
- Integrates autoDream for overnight memory consolidation
- Access via `tengu_kairos_cron` and `tengu_kairos_cron_durable` flags

### BUDDY — Tamagotchi Companion
- Deterministic gacha system using **Mulberry32 PRNG** seeded from `userId` hash with salt `'friend-2026-401'`
- 18 species across 5 rarity tiers (Common → Legendary) plus 1% shiny variants
- Procedural stats: DEBUGGING, PATIENCE, CHAOS, WISDOM, SNARK (each 0-100)
- Visual: ASCII art sprites, 5 lines × 12 characters, with animation frames
- 6 eye styles, 8 hat options (rarity-gated)
- AI-generated "soul" personality description written by Claude on first hatch
- Gate: `BUDDY` compile-time feature flag. Reportedly targeted for May 2026 release.

### ULTRAPLAN — Remote Cloud Planning
- Farms complex exploration to a **CCR (Claude Code Remote)** instance using **Opus 4.6**
- Maximum session: 30 minutes with 3-second polling intervals
- Browser-based approval workflow before execution proceeds
- Results returned to local terminal via `__ULTRAPLAN_TELEPORT_LOCAL__` sentinel value
- Keyword detection prevents false positives in code paths and identifiers

### Agent Triggers / Cron Tools
- `CronCreateTool`, `CronDeleteTool`, `CronListTool` — agents can schedule their own future executions mid-conversation
- Gate: `AGENT_TRIGGERS` feature flag

### Speculative Execution
- After Claude generates a response suggestion, a background API call forks and begins executing the predicted next prompt
- Tags: `querySource: "speculation"`, `forkLabel: "speculation"`
- File writes redirected to overlay filesystem at `~/.claude/speculation/<pid>/<speculation_id>/`
- On first write, original file is copied to overlay; all subsequent ops use overlay
- On acceptance, overlay copies back to real filesystem
- Freely allowed speculatively: Read, Glob, Grep, ToolSearch, LSP, TaskGet, TaskList
- Blocked speculatively: writes outside working directory, Bash requiring approval
- Limits: 20 tool-use turns max, 100 messages max before forced abort
- Pipelining: generates next suggestion immediately after current, stays multiple steps ahead
- Gate: `tengu_speculation` + `tengu_chomp_inflection`

---

## 9. Anti-Distillation (ANTI_DISTILLATION_CC)

The most strategically sensitive leaked system. `ANTI_DISTILLATION_CC` injects `anti_distillation: ['fake_tools']` into every API request, causing the server to **silently inject decoy tool definitions into the model's system prompt**.

The intent: poison training data for competitors attempting to distill Claude's capabilities by scraping its outputs. Any model trained on Claude Code's outputs would learn from contaminated tool definitions and system prompts. Context: Anthropic documented industrial-scale distillation campaigns by DeepSeek, Moonshot, and MiniMax — over 16 million exchanges via ~24,000 fraudulent accounts.

The fake tool definitions are not visible to users or to Claude itself in normal operation — they appear only in the API request payload on the server side.

---

## 10. Undercover Mode

Anthropic employees automatically enter Undercover Mode when working in public/open-source repositories. The system detects whether the current repo matches an internal allowlist; if not, it activates.

**System prompt instruction (verbatim from leak)**: "You are operating UNDERCOVER in a PUBLIC/OPEN-SOURCE repository. Your commit messages, PR titles, and PR bodies MUST NOT contain ANY Anthropic-internal information. Do not blow your cover."

Specifically suppressed:
- Internal model codenames (Capybara, Tengu, and others — these are encoded as `String.fromCharCode(...)` to evade internal leak detectors even in the undercover module itself)
- Unreleased version numbers
- Internal tooling references
- `Co-Authored-By: Claude` attribution lines in commits

No force-OFF option — it defaults conservative. 22 internal repository names were exposed in the allowlist, which is itself a secondary leak. Undercover mode is implemented in `utils/undercover.ts`.

---

## 11. Feature Flag System

### Infrastructure
GrowthBook (migrated from Statsig) for runtime remote configuration. Two evaluation patterns:
- `feature('FLAG_NAME')` — compile-time dead code elimination (Bun removes dead branches at build time for compile-time flags)
- `getFeatureValue_CACHED_MAY_BE_STALE()` — runtime GrowthBook evaluation with aggressive caching to avoid blocking the main loop; stale data is explicitly acceptable for feature gates

### Naming Convention
`tengu_` prefix for all runtime flags. Names use random word pairs (`tengu_frond_boric`, `tengu_malort_pedway`) to obscure purpose from external observers.

### Notable Flags (32 compile-time + 200+ runtime)

**Compile-time (strip from binary if disabled)**:
- `BUDDY`, `KAIROS`, `VOICE_MODE`, `COORDINATOR_MODE`, `WORKFLOW_SCRIPTS`, `BYOC_RUNNER`, `CHICAGO_MCP` (computer use), `AGENT_TRIGGERS`, `KAIROS_GITHUB_WEBHOOKS`, `BG_SESSIONS`

**Runtime (GrowthBook)**:
| Flag | Controls |
|---|---|
| `tengu_amber_quartz` | Voice mode availability |
| `tengu_penguins_off` | Kill switch for Penguin (fast) Mode |
| `tengu_marble_sandcastle` | Restrict fast mode to native binary installs |
| `tengu_amber_flint` | Agent Teams / Swarm capability |
| `tengu_scratch` | Coordinator scratch directory sharing |
| `tengu_speculation` | Speculative execution |
| `tengu_chomp_inflection` | Prompt suggestions |
| `tengu_kairos_cron` | KAIROS scheduled execution |
| `tengu_kairos_cron_durable` | KAIROS persistent cron (survives machine restart) |
| `tengu_onyx_plover` | autoDream consolidation |
| `tengu_ccr_bridge` | Remote Control (CCR) |
| `tengu_malort_pedway` | Computer use (Playwright browser control) |
| `tengu_thinkback` | Extended thinking |
| `tengu_iron_gate_closed` | Kill switch (purpose unclear) |

**Penguin Mode**: Internal name for "fast mode" — the higher-cost API tier ($30/M input vs $5/M normal, same Opus 4.6 model). Endpoint: `/api/claude_code_penguin_mode`. Disabled for custom API base URL users.

**Capybara**: Internal codename for a model version. Encoded as `String.fromCharCode(99,97,112,121,98,97,114,97)` to evade internal leak detectors.

**Tengu**: The project codename for Claude Code itself. A Japanese supernatural creature known for being simultaneously dangerous and a teacher — a deliberate choice.

---

## 12. Security Model

### Permission Architecture
- Risk classification (LOW/MEDIUM/HIGH) per tool action
- `classifyYoloAction()`: LLM-based self-authorization in auto-approval mode
- Protected system files unconditionally blocked from modification
- Path traversal prevention: URL-encoded traversals, Unicode normalization attacks, backslash injection, case-insensitive path manipulation — all handled
- `USER_TYPE=ant` environment variable unlocks internal-only functionality
- `CLAUDE_CODE_ABLATION_BASELINE` bypasses safety features entirely (ablation testing escape hatch)

### Prompt Injection Defense
Tool outputs processed through a `PostToolUse` hook with runtime injection detection before Claude processes results. The permission explainer makes a separate LLM call to explain risks before user approval — a sandboxed analysis step.

### Sandboxing
No OS-level sandboxing (no seccomp, no container). Sandboxing for speculative execution is purely a userspace overlay filesystem. The permission system is policy-based, not kernel-enforced. This is a significant gap — a compromised tool can do anything the user account can do.

### Known CVEs
- Multiple prompt injection CVEs documented (CVE-2025-54794, CVE-2025-54795 — "InversePrompt" attack)
- Zero-click XSS prompt injection via VS Code extension (patched March 2026)
- Remote code execution and API key exfiltration via malicious repository content (patched Feb 2026)

---

## 13. Interesting Engineering Decisions

### Regex Sentiment Analysis
Sentiment analysis for tone classification (used in telemetry and UX adaptation) is implemented with **regex patterns**, not an LLM call. Rationale: deterministic, zero latency, zero cost. Engineering tradeoff: coarse but fast. No blocking of the main loop.

### Zod v4
The migration to Zod v4 (which introduced breaking schema changes and a new `z.object()` API) was made throughout the codebase for performance gains in schema validation. Zod v4 instantiation is lazy-loaded to reduce startup time impact.

### Mulberry32 PRNG
The BUDDY system uses Mulberry32, a fast 32-bit PRNG. Seeded from a stable hash of `userId`, making companion generation deterministic per user — same pet always regenerates from the same seed. Salt `'friend-2026-401'` is hardcoded.

### Tool Registry Alphabetical Sort
Tools are sorted alphabetically in the registry as a prompt caching optimization. Since tool definitions appear in the system prompt, consistent ordering maximizes cache hit rates across sessions.

### Native Zig Module
The native Bun installer includes a Zig module. A known bug: it corrupts conversation content when specific sentinel values appear in prompts, breaking prompt caching. The `__ULTRAPLAN_TELEPORT_LOCAL__` sentinel is one known trigger value.

### 785KB Entry Point
`main.tsx` at 785KB is an architectural smell — likely accumulated over time through feature flag guards and runtime mode detection all concentrated in one file rather than properly split at module boundaries.

### Memory Efficiency
Seven concurrent Claude Code processes consume 5.3 GB RAM collectively. No shared memory between processes; each runs a full Bun runtime. This is a significant resource cost for multi-agent workflows.

---

## Recommended Stack (for Building Comparable Systems)

| Component | Choice | Rationale |
|---|---|---|
| Runtime | Bun 1.2+ | Fast startup, native TS, dead-code elimination |
| Language | TypeScript 5.x | Full ecosystem parity |
| Terminal UI | Ink 4.x + Yoga | Proven, React mental model |
| Validation | Zod v4 | Type-safe, fast, battle-tested in this exact domain |
| Feature flags | GrowthBook | What Anthropic uses; supports runtime + compile-time patterns |
| LLM client | Anthropic SDK with streaming | Native streaming tool use support |
| Memory | File-based YAML + MEMORY.md index | Simpler than vector DB for this scale |
| Multi-agent IPC | File-based with lock files | What works in production; message bus is over-engineering |
| Permissions | Explicit allow/deny/ask per tool+path | Do not implement YOLO auto-approve |

---

## Open Questions

1. **How does the server-side fake tool injection actually work?** The client sends `anti_distillation: ['fake_tools']` but the server logic is not exposed — only the client-side flag is in the leak.
2. **What is `tengu_iron_gate_closed`?** The flag name suggests a kill switch but its target is not documented in any analysis.
3. **What are the 22 internal repos** in the undercover mode allowlist? These were briefly visible before the archive was partially scrubbed.
4. **What is `TungstenTool`?** Listed as internal-only but not described anywhere in the analysis.
5. **How does ULTRAPLAN handle secrets?** The CCR execution happens on Anthropic cloud infrastructure with your code — key management not documented.
6. **Is autoDream reading session transcripts GDPR-compliant?** The gather phase explicitly reads JSONL transcript files from past sessions. Regulatory questions for enterprise users.
7. **What triggers the Zig module corruption?** Only `__ULTRAPLAN_TELEPORT_LOCAL__` has been identified; other sentinel values are unknown.

---

## Sources

- [GitHub: Kuberwastaken/claude-code — Primary Archive](https://github.com/Kuberwastaken/claude-code)
- [DEV Community: Claude Code's Entire Source Code Was Just Leaked via npm Source Maps](https://dev.to/gabrielanhaia/claude-codes-entire-source-code-was-just-leaked-via-npm-source-maps-heres-whats-inside-cjo)
- [DEV Community: Claude Code's Entire Source Code Just Leaked — 512,000 Lines Exposed](https://dev.to/evan-dong/claude-codes-entire-source-code-just-leaked-512000-lines-exposed-3139)
- [VentureBeat: Claude Code's source code appears to have leaked](https://venturebeat.com/technology/claude-codes-source-code-appears-to-have-leaked-heres-what-we-know/)
- [Hacker News Discussion](https://news.ycombinator.com/item?id=47584540)
- [Sathwick.xyz: Reverse-Engineering Claude Code Deep Dive](https://sathwick.xyz/blog/claude-code.html)
- [ccleaks.com: Claude Code Hidden Features](https://www.ccleaks.com/)
- [Dreadheadio: I Read the Leaked Claude Code Source](https://dreadheadio.github.io/claude-code-roadmap/claude-code-roadmap-blog.html)
- [claudefa.st: Auto Dream Memory Feature](https://claudefa.st/blog/guide/mechanics/auto-dream)
- [DEV Community: Does Claude Code Need Sleep? Auto-Dream Feature](https://dev.to/akari_iku/does-claude-code-need-sleep-inside-the-unreleased-auto-dream-feature-2n7m)
- [MindStudio: What Is Claude Code AutoDream?](https://www.mindstudio.ai/blog/what-is-claude-code-autodream-memory-consolidation-2)
- [Geeky Gadgets: AutoDream Memory Files](https://www.geeky-gadgets.com/claude-autodream-memory-files/)
- [Paddo.dev: Claude Code's Hidden Multi-Agent System](https://paddo.dev/blog/claude-code-hidden-swarm/)
- [ZeroToPete: I Found a Hidden Feature Called Speculation](https://www.zerotopete.com/p/i-found-a-hidden-feature-in-claude)
- [DecodeClaude: Inside Claude Code's Compaction System](https://decodeclaude.com/compaction-deep-dive/)
- [DEV Community: We Reverse-Engineered 12 Versions of Claude Code](https://dev.to/kolkov/we-reverse-engineered-12-versions-of-claude-code-then-it-leaked-its-own-source-code-pij)
- [UpGuard: YOLO Mode Hidden Risks in Claude Code Permissions](https://www.upguard.com/blog/yolo-mode-hidden-risks-in-claude-code-permissions)
- [GitHub: claude-code-changelog feature flags](https://github.com/marckrenn/claude-code-changelog/blob/main/cc-flags.md)
- [GitHub: Claude Code feature flag issues — tengu_amber_quartz voice mode](https://github.com/anthropics/claude-code/issues/33580)
- [Cybernews: Full source code for Anthropic's Claude Code leaks](https://cybernews.com/security/anthropic-claude-code-source-leak/)
- [MLQ.ai: Anthropic's Claude Code Exposes Source Code Through Packaging Error for Second Time](https://mlq.ai/news/anthropics-claude-code-exposes-source-code-through-packaging-error-for-second-time/)
- [GitHub: Piebald-AI Claude Code System Prompts](https://github.com/Piebald-AI/claude-code-system-prompts)
- [SecurityWeek: Claude Code Flaws Exposed Developer Devices](https://www.securityweek.com/claude-code-flaws-exposed-developer-devices-to-silent-hacking/)
- [Anthropic: Detecting and Preventing Distillation Attacks](https://www.anthropic.com/news/detecting-and-preventing-distillation-attacks)
- [Threads: sakeeb.rahman — autoDream technical breakdown](https://www.threads.com/@sakeeb.rahman/post/DWSKjMoESz2/)
- [GitHub: grandamenium/dream-skill — autoDream replication](https://github.com/grandamenium/dream-skill)
