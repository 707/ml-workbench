# project-template: Technical & Retrospective Workflow Document

> A personal fork of Everything Claude Code (ECC), adapted with influences from how-i-code, for structured end-to-end AI-assisted development.

---

## 1. What is project-template?

`project-template` is a **per-project AI development scaffolding system** designed to be dropped into any new codebase and immediately impose a disciplined, structured workflow for building software with Claude Code and Gemini CLI. It is not a library, a package, or a global tool — it is a living directory that travels with the project.

It was built to solve four recurring problems that emerge when developing with AI:

| Problem | Symptom | How project-template Solves It |
|---------|---------|-------------------------------|
| **Context Pollution** | Planning discussions, old approaches, and dead ideas fill the context window during implementation | Plans live in the issue tracker + `.ai/tickets/`. Implementation starts in a fresh context. |
| **Scope Creep** | Features balloon because AI eagerly extends what you ask | Atomic issue structure + "Confirmed Plan" as authoritative — never re-planned mid-implementation |
| **Incomprehensible Output** | Code that works but nobody understands, including the author | Comprehensibility checkpoints + code-reviewer agent with 80%+ confidence threshold before merge |
| **Lost Context Across Sessions** | Every new Claude session starts from zero, re-explaining the same context | Ticket context files (`.ai/tickets/GH-{N}/context.md`) + session summaries + SessionStart hook |

The project-template was built after iterating through two prior workflow phases: the **Klue Dev workflow** (a manual, dual-agent approach using Gemini for planning and Claude for implementation) and a period of adopting **Everything Claude Code (ECC)** as a global foundation. project-template represents the distillation of both into a per-project, opinionated, self-contained system.

---

## 2. Lineage & Influences

### 2.1 How BUILDING-SETUP.md Came from how-i-code

The `how-i-code` project (by nad, inspired by Eddie Belaval's concept of a build journal) introduced a powerful idea: instead of writing a project documentation file manually, have Claude Code **run a self-installing wizard** that explores the project, interviews the developer, and generates a personalized `BUILDING.md` journal that auto-updates as the project progresses.

`BUILDING-SETUP.md` in project-template is a direct adaptation of this concept. The nine-step wizard:

1. Introduces the concept of BUILDING.md to the developer
2. Asks permission to autonomously explore the project structure
3. Runs the autonomous exploration (manifest, git history, file structure, existing docs)
4. Presents findings and a proposed journal structure
5. Asks 2-3 high-level questions (what to track, philosophy, depth preference)
6. Optionally deep-dives into specific areas
7. Generates a personalized `BUILDING.md`
8. Embeds an auto-update protocol as HTML comments (invisible to readers, readable by Claude)
9. Offers an optional origin story interview, then self-deletes

The auto-update protocol is the key innovation: it defines exactly when Claude should add to the journal (new feature shipped, architecture decision made, significant bug fixed, milestone reached, lesson learned, major refactor) and when it should NOT (typo fixes, routine tests, minor dependency bumps). It also defines a check-in system every 5 auto-update entries that pauses for human reflection.

This approach means BUILDING.md is never a chore — it writes itself during normal development, capturing the arc of the project automatically.

### 2.2 How ECC Informed the Foundation

Everything Claude Code (ECC) v1.8.0, developed by Affaan Mustafa (Anthropic Hackathon winner), provided the foundational patterns that project-template is built on:

- **Agent architecture**: The pattern of specialized agents with YAML frontmatter (planner, tdd-guide, code-reviewer, security-reviewer, etc.) and the discipline of invoking them via slash commands
- **Slash command system**: The pattern of `.claude/commands/*.md` files as structured, documented workflow entry points
- **Hook system**: The event-driven quality gate architecture (PreToolUse, PostToolUse, Stop, SessionStart, PreCompact)
- **Skills library**: The concept of domain-specific expertise files (SKILL.md) organized by stack, used to pre-load reusable patterns into context
- **TDD workflow**: The RED → GREEN → REFACTOR discipline enforced by the tdd-guide agent
- **Code review discipline**: 80%+ confidence threshold, severity-ranked issues (CRITICAL/HIGH/MEDIUM/LOW), approval criteria
- **Model routing philosophy**: Haiku for exploration, Sonnet for coding, Opus for architectural decisions

These patterns were not invented for project-template — they were battle-tested in ECC over 10+ months of daily real-world use. project-template inherited them wholesale, then stripped and extended based on personal workflow needs.

---

## 3. project-template as a Personal Fork of ECC

### 3.1 What Was Stripped

ECC is a community-facing, distribution-ready toolkit. project-template is a personal system. The following were deliberately removed:

| Removed from ECC | Reason |
|-----------------|--------|
| `install.sh` script + npm package | Per-project scaffolding doesn't need distribution |
| `rules/typescript/`, `rules/python/`, `rules/golang/`, `rules/swift/` | Skills library handles language-specific patterns more elegantly |
| `README.md`, `CONTRIBUTING.md`, `SPONSORING.md`, `CODE_OF_CONDUCT.md` | Not a public project |
| NanoClaw REPL (`/claw`) | Specialized REPL not needed in standard workflow |
| `loop-operator` + `chief-of-staff` agents | Autonomous loop architecture not adopted |
| 23 commands from ECC's 40 | Reduced to ~17 focused commands covering the actual development loop |
| 6 agents from ECC's 16 | Reduced to 10 core agents (removed go-reviewer, go-build-resolver, python-reviewer, doc-updater, loop-operator, chief-of-staff) |
| `mcp-configs/` | MCP selection is per-project; not baked into the template |
| `.cursor/`, `.codex/`, `.opencode/` configs | Single IDE focus |
| Multi-instance parallelization patterns | Simpler single-agent-per-task model preferred |

### 3.2 What Was Added

These features do not exist in ECC and were built specifically for project-template:

#### The Ticket Context System (`.ai/tickets/`)

The single most important addition. ECC has session summaries and continuous learning, but no mechanism for preserving a *specific implementation plan* across sessions without re-planning.

The ticket context system works like this:

```
.ai/tickets/
├── active.md                    # Per-developer: current ticket ID (gitignored)
├── GH-42/
│   └── context.md              # Shared: plan + state + handoff instructions
└── GH-43/
    └── context.md
```

Each `context.md` file contains:
- **Confirmed Plan** (the planner's output, marked as authoritative — never re-planned)
- **Files to Read Before Starting** (exact files needed for this ticket)
- **Current State** (checkboxes: completed, in-progress, notes)
- **Handoff Instructions** (exactly where to resume next session)

When `/tdd GH-42` is invoked, the tdd-guide agent reads `.ai/tickets/GH-42/context.md` first. It pulls the real issue body from GitHub/Linear. It treats "Confirmed Plan" as law. It picks up from "In Progress" rather than starting from scratch. At session end, `/handoff` updates the context file. The next session — whether hours or days later — resumes with full fidelity.

This solves the "lost context" problem at the implementation level, not just the session summary level.

#### Dual-Platform Agent Generation

ECC is Claude-native. project-template supports both Claude Code and Gemini CLI by storing agent instruction bodies in a platform-agnostic location (`.ai/agents/`) and generating platform-specific versions:

```
scripts/gen-agents.js
  ↓
reads: .ai/agents/planner.md       (platform-agnostic body)
reads: scripts/agent-config.json  (per-platform frontmatter config)
writes: .claude/agents/planner.md  (with Claude Code YAML frontmatter)
writes: .gemini/agents/planner.md  (with Gemini CLI frontmatter)
```

`scripts/agent-config.json` maps each agent to tool lists and model names per platform:

```json
{
  "planner": {
    "claude": {
      "name": "planner",
      "tools": ["Read", "Grep", "Glob"],
      "model": "sonnet"
    },
    "gemini": {
      "name": "planner",
      "kind": "TASK",
      "tools": ["read_file", "search_files", "list_files"],
      "model": "gemini-2.5-pro",
      "max_turns": 20
    }
  }
}
```

Edit an agent's instructions once in `.ai/agents/`, run `node scripts/gen-agents.js`, and both platforms are updated.

#### GEMINI.md with Startup/Shutdown Rituals

Gemini CLI has no hook system. Where Claude Code automatically runs `session-start.js` on session open, Gemini CLI requires explicit manual rituals. GEMINI.md codifies these:

**Startup Ritual** (run at the beginning of every Gemini session):
1. Read `.ai/tickets/active.md` to identify current ticket
2. Read `.ai/tickets/{ID}/context.md` to load plan and state
3. Confirm orientation and identify next action
4. Report readiness

**Shutdown Ritual** (run before ending every Gemini session):
1. Run `/handoff` to update current state
2. Verify context.md is updated with progress
3. Commit WIP if needed

This gives Gemini sessions the same context continuity that Claude Code achieves automatically via hooks — it just requires discipline rather than automation.

#### `.claude/project.json` — Per-Developer Tracker Config

Each developer on a project has their own tracker configuration, gitignored so it doesn't conflict:

```json
{
  "tracker": "github",
  "githubRepo": "owner/repo",
  "linearTeam": "ENG",
  "linearProject": "Q1 2026"
}
```

`/plan` and `/tdd` read this file to know where to create issues and where to fetch issue bodies. Switching between GitHub and Linear is a one-line edit.

#### Skill Opt-In via Tech Stack Declaration

ECC requires running `install.sh typescript python` to install language-specific rules. In project-template, skills are opt-in by declaring the tech stack in CLAUDE.md §4:

```markdown
## §4 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React 18, TypeScript |
| Backend | Node.js, Prisma |
| Database | PostgreSQL (Supabase) |
| Testing | Vitest, Playwright |
```

Skills in `skills/web/`, `skills/database/`, etc. are only activated when the corresponding stack is declared. This prevents irrelevant skills from polluting the context.

### 3.3 Key Philosophy Shift: Global Toolkit vs Project Scaffolding

| Dimension | ECC | project-template |
|-----------|-----|-----------------|
| **Install scope** | Global user-level (`~/.claude/`) | Per-project (`.claude/` in repo) |
| **Distribution** | npm package + install.sh | Fork and adapt |
| **Agent management** | 16 agents, install per-language | 10 agents, platform-generated from single source |
| **MCP management** | 14 MCPs, enable/disable per project | No MCPs baked in; per-project decision |
| **Skill activation** | install.sh per-language | Tech stack declaration in CLAUDE.md |
| **Ticket context** | Session summaries only | Ticket context files + session summaries |
| **Platform support** | Claude Code only | Claude Code + Gemini CLI |
| **Target user** | Any Claude Code developer (community) | Personal workflow |

---

## 4. Token Usage: Before vs After Adopting ECC

### 4.1 Before ECC (Klue Dev Era)

Before adopting ECC patterns, every session started with significant overhead:

- **Pattern re-explanation**: Each new session required re-explaining code style, testing philosophy, commit conventions, and agent roles. This could consume 10-15% of the context window before any work was done.
- **No model routing**: Every request went to the same model regardless of complexity. Exploratory searches cost the same as complex architectural analysis.
- **No skills library**: Domain-specific patterns (e.g., "how we do database migrations here") existed only in the developer's head or in previous chat logs.
- **Ad-hoc MCP usage**: MCPs were enabled globally, consuming 50-70K tokens of context window for schema loading even when not needed for the current task.
- **No suggest-compact**: Context windows filled silently until the AI started degrading, with no proactive warnings.

---

## 5. Memory Note — 2026-03-23 (GH-2 Follow-up)

Post-ticket UX and tokenizer clarity improvements were completed with explicit RED→GREEN TDD:

- Added a readable token view toggle in `workbench/tokenizer.py` for Single and Compare tabs.
- In readable mode, special tokens (like BOS) are hidden by default and token IDs are decoded to human-readable fragments.
- Updated the comparison prompt area in `workbench/app.py`:
  - `Preset Questions` wording replaced with `Input Prompt`.
  - Custom prompt input moved into the same prompt section.
- Tests added first (RED), then implementation updated to pass (GREEN).
- **Manual context management**: Knowing when to `/compact` or start a fresh session was a guessing game.

Rough estimate: **20-30% of every session's token budget was overhead** — re-establishing context that should have been pre-loaded.

### 4.2 After Adopting ECC Patterns (project-template)

The ECC-derived patterns in project-template address each of these inefficiencies:

**Model Routing (~30-50% cost reduction on exploration tasks)**
- Haiku for codebase exploration and simple searches (90% of Sonnet capability, 3x lower cost)
- Sonnet for multi-file implementation (best coding balance)
- Opus for architectural decisions and complex analysis (reserved for when depth matters)

**Skills Library (~40-60% reduction in pattern re-explanation overhead)**
- Skills pre-load reusable domain patterns into context on first invocation
- Once `skills/web/api-design` is in the session, API design patterns don't need re-explaining
- Skills are amortized across sessions — written once, applied everywhere

**SessionStart Hook (eliminates manual context re-establishment)**
- Automatically loads the previous session summary on startup
- Automatically loads the active ticket context if one is set
- Automatically reminds about BUILDING.md if it exists
- Developer sees "good morning, here's where we left off" without typing anything

**suggest-compact.js (prevents invisible context degradation)**
- Warns at 50+ tool calls, re-warns every 25 calls past that
- Developers know exactly when to `/compact` before quality degrades
- Prevents the "AI started hallucinating" session that wastes 45 minutes

**Strategic MCP usage (<10 active per project)**
- MCPs are not baked into project-template; they're an opt-in per-project decision
- Recommended ceiling: under 10 active MCPs per project
- Replacing MCPs with CLI + skills where possible (e.g., `gh` CLI + github skill instead of GitHub MCP)

**Ticket Context System (eliminates re-planning overhead entirely)**
- `/tdd GH-42` never needs to re-read the requirements from the developer
- All context is pre-loaded from `.ai/tickets/GH-42/context.md`
- Rough estimate: saves 5-15% of context window per implementation session

**Overall**: The transition from ad-hoc AI usage to ECC-pattern-based project-template reduced per-session overhead from ~20-30% to approximately **5-10%** — a meaningful improvement across a long project.

---

## 5. MCP Approach: Before and After

### 5.1 The Problem with Ad-Hoc MCPs

In the Klue Dev era, MCPs were configured globally with no per-project control. The result:
- Every session loaded all MCP schemas regardless of what was being built
- With 10-15 MCPs enabled, 50-70K tokens of context window were consumed before writing a line of code
- MCPs added latency to tool invocations
- Debugging "why did Claude not use the MCP" was opaque

### 5.2 The ECC MCP Philosophy

ECC v1.8.0 established a more disciplined approach, documented in the shortform guide:
- Configure 20-30 MCPs in the config file (they're not loaded until enabled)
- **Keep under 10 enabled per project** at any time
- Use `disabledMcpServers` in project config to disable MCPs not relevant to this codebase
- **Replace MCPs with CLI + skills** where possible (e.g., `gh` CLI + github-skill replaces GitHub MCP for most operations)
- Watch context window: if remaining context drops below 70K, an enabled MCP might be the culprit

The insight is that most developers over-index on MCPs because they're exciting — but a `gh` CLI call in a Bash tool invocation costs far fewer tokens than an MCP tool invocation with a full schema header.

### 5.3 In project-template

project-template deliberately does not bundle MCP configs. Instead:
- `.claude/project.json` configures the issue tracker (GitHub or Linear)
- MCPs are a per-project decision, documented as a consideration in USER-GUIDE.md
- The ticket context system replaces what many developers used MCPs for (persistent context across sessions)

The recommended MCP setup for a typical web app using project-template:
- `supabase` (if using Supabase) — direct database operations
- `github` — PR management beyond what `gh` CLI covers
- `context7` — live documentation lookup for unfamiliar libraries
- Everything else: use CLI tools + skills

---

## 6. The Hook System: Eight Quality Gates

project-template's hook system is derived from ECC's hook architecture but simplified to eight non-blocking quality gates:

### PreToolUse Hooks

| Hook | Trigger | Behavior |
|------|---------|----------|
| `git-push-reminder.js` | Before Bash (git push) | Reminds to review changes before pushing; non-blocking |
| `doc-file-warning.js` | Before Write (*.md, *.txt) | Warns about non-standard documentation files; non-blocking |
| `suggest-compact.js` | Before any Edit/Write | Counts tool calls; warns at 50+, re-warns every 25 past that |

### PostToolUse Hooks

| Hook | Trigger | Behavior |
|------|---------|----------|
| `post-edit-format.js` | After Edit/Write on JS/TS | Detects Biome or Prettier config, auto-formats silently |
| `post-edit-typecheck.js` | After Edit/Write on TS | Finds nearest tsconfig.json, runs `tsc --noEmit`, reports on edited file only |
| `post-edit-console-warn.js` | After Edit/Write | Scans modified files for `console.log`, excludes test/config/scripts/ |

### Lifecycle Hooks

| Hook | Trigger | Behavior |
|------|---------|----------|
| `session-start.js` | New session | Loads previous session summary, loads active ticket context, reminds about BUILDING.md |
| `session-end.js` | Session ends | Extracts summary from JSONL transcript, saves to `~/.claude/sessions/{date}-{id}-session.tmp` |

**Design principles for all hooks:**
- **Non-blocking**: Never use exit code 2 (blocking) unless absolutely necessary; warn and let the developer decide
- **Fail gracefully**: If the hook errors, it logs to stderr but doesn't interrupt the session
- **Fast**: No network calls; hooks run synchronously in the hot path
- **Cross-platform**: Windows/macOS/Linux safe paths throughout

The `suggest-compact.js` hook is particularly valuable. Context degradation is the silent killer of AI sessions — the AI starts hallucinating or repeating itself and the developer doesn't know why. By proactively suggesting `/compact` at 50 tool calls (roughly 1-2 hours of active development), this hook prevents the phenomenon entirely.

---

## 7. The Ticket Context System: The Key Innovation

The ticket context system is the feature that most distinguishes project-template from ECC and from ad-hoc AI development workflows.

### 7.1 The Problem It Solves

In a typical AI development session without this system:
- Session 1 (Planning): Developer and AI plan a feature, agree on approach
- *Session ends*
- Session 2 (Implementation): Developer has to re-explain the plan, re-establish what files are relevant, re-confirm which approach was chosen
- *Mid-session context fills*
- Session 3 (Continuation): Repeat the re-establishment overhead again

This is not just inefficient — it's dangerous. Re-explaining plans leads to plan drift. The AI might suggest a slightly different approach because it doesn't remember the exact reasoning from Session 1. The "Confirmed Plan" gets eroded.

### 7.2 How the System Works

```
Session 1 (Planning)
────────────────────
User: /plan

planner agent:
  → Analyzes codebase
  → Creates implementation plan
  → WAITS for user confirmation (never starts coding)

User: Confirms plan

Claude:
  → Creates GitHub/Linear issue
  → Writes .ai/tickets/GH-42/context.md with:
     • Confirmed Plan (authoritative, immutable)
     • Files to Read Before Starting
     • Current State: empty
     • Handoff Instructions: "Start with Phase 1"

────────────────────────────────────────────────────

Session 2 (Implementation — fresh context)
──────────────────────────────────────────
User: /tdd GH-42

tdd-guide agent:
  → Reads .ai/tickets/GH-42/context.md
  → Pulls real issue body from GitHub
  → Creates branch: feature/GH-42-{slug}
  → Reports: "Confirmed Plan is X. In Progress: Phase 1. Starting with RED test..."

[Works through RED → GREEN → REFACTOR cycles]
[Commits after each cycle]

End of session:
User: /handoff

Claude:
  → Updates .ai/tickets/GH-42/context.md:
     • Marks Phase 1 complete ✓
     • Notes Phase 2 as In Progress
     • Writes precise handoff instructions

────────────────────────────────────────────────────

Session 3 (Continuation — fresh context)
──────────────────────────────────────────
User: /tdd GH-42

tdd-guide agent:
  → Reads .ai/tickets/GH-42/context.md
  → Reports: "Phase 1 complete. In Progress: Phase 2, Step 1. Resuming..."
  → Continues exactly where Session 2 left off
```

### 7.3 The "Confirmed Plan is Authoritative" Rule

This is the most important discipline in the system. Once a plan is confirmed and written to `context.md`, it is **never re-planned mid-implementation**. The tdd-guide agent is explicitly instructed to treat the Confirmed Plan as law, even if it discovers a "better" approach during implementation.

Why? Because re-planning mid-implementation is how scope creep enters. It's how 3-day features become 3-week features. The plan may be suboptimal — but finishing an atomic, well-understood plan and then improving it in the next ticket is always better than abandoning plans mid-stream.

If the plan needs to change, the developer creates a new ticket with a revised plan. The old ticket closes with the original scope delivered.

---

## 8. Comparing project-template with the Klue Dev Workflow

See also: `Klue Dev/WORKFLOW-RETROSPECTIVE.md` for the Klue Dev perspective on this comparison.

| Dimension | Klue Dev Workflow (Before) | project-template (After) |
|-----------|--------------------------|--------------------------|
| **Workflow installation** | Ad-hoc, per-project setup | Drop in `.claude/`, `.gemini/`, `.ai/`, run gen-agents.js |
| **Context persistence** | `.specs/NOT-*.md` files + `.project_wisdom/` | `.ai/tickets/GH-{N}/context.md` + session summaries |
| **Agent roles** | Gemini = CTO (plan only), Claude = Dev (implement) | Single AI (Claude or Gemini) + specialized sub-agents per task |
| **Planning format** | Markdown spec files (NOT-*.md) with checkboxes | GitHub/Linear Issues + ticket context files |
| **Plan enforcement** | Honor system (spec as contract) | "Confirmed Plan" field in context.md, tdd-guide agent instructed never to re-plan |
| **Institutional memory** | `workflow_learnings.md` + PDRs + session logs | BUILDING.md (auto-updating) + skills/ library + session summaries |
| **Issue tracking** | Linear CLI (two-way sync) | GitHub or Linear via `project.json`, real issues created by `/plan` |
| **Hook system** | Pre-commit hooks (security focus) | Full Claude Code event system (8 quality gates, automatic) |
| **MCP usage** | Linear CLI + basic tools | Per-project decision; template has no bundled MCPs |
| **Token strategy** | Persona separation (two AIs, two contexts) | Model routing (one AI, right model for right task) |
| **Quality gates** | Manual CONTRIBUTING.md rules + pre-commit | Automated (typecheck, format, console.log, suggest-compact) |
| **Cross-session continuity** | Specs survive resets + project_wisdom | Ticket context.md + SessionStart hook auto-loads state |
| **Setup time for new project** | Days (spec system, workflow files, Linear setup) | Hours (fork template, fill CLAUDE.md §4, run gen-agents.js) |
| **Learning capture** | Dated session logs, PDRs, workflow_learnings.md | BUILDING.md auto-updates, skills library, session summaries |
| **Security enforcement** | CONTRIBUTING.md as hard constraints | code-reviewer + security-reviewer agents, pre-commit hooks |
| **Platform** | Claude (implement) + Gemini (plan) — always both | Claude or Gemini — either works; both available |

### What Klue Dev Did Better

- **Role separation as a quality gate**: Having Gemini own architecture and Claude own implementation created a natural design review step. Neither AI could short-circuit the other's domain. project-template consolidated this into sub-agents, which is more efficient but loses the cross-model "skeptic" check.
- **Spec files as human-readable contracts**: `.specs/NOT-*.md` files were readable by developers in any editor. The `.ai/tickets/context.md` format serves the same purpose but is AI-first rather than human-first.
- **Workflow learnings as immune system**: `workflow_learnings.md` explicitly captured failures in a format that fed back into future sessions. project-template's BUILDING.md captures successes more than failures.
- **Deep product decision records**: PDRs (why each major decision was made) are more durable than session summaries. project-template doesn't have a direct equivalent unless explicitly added.

### What project-template Does Better

- **Zero setup cost per session**: No startup ritual required; hooks handle it automatically.
- **Plan immutability**: "Confirmed Plan is authoritative" is enforced by the tdd-guide agent, not by developer discipline.
- **Automated quality gates**: Format, typecheck, console.log, suggest-compact all happen without developer action.
- **Transferable to new projects**: Fork the template, fill in the tech stack, done. Klue Dev's workflow was deeply entangled with Klue's specific product.
- **Skills library scales**: As you build more projects with the template, the skills library grows. Klue Dev's project_wisdom was project-specific.
- **Dual-platform without context duplication**: Either Claude or Gemini can run the same workflow using the same ticket context files.

---

## 9. Quick Reference

### Core Commands

| Command | Agent Invoked | When |
|---------|--------------|------|
| `/plan` | planner (Sonnet) | Feature planning; creates issue + ticket context |
| `/tdd GH-42` | tdd-guide (Sonnet) | Implementation; loads ticket context |
| `/code-review` | code-reviewer (Sonnet) | After implementation; before PR |
| `/build-fix` | build-error-resolver (Sonnet) | TypeScript/build errors |
| `/checkpoint` | — | Named git snapshot before context clear |
| `/handoff` | — | Update ticket context before session end |
| `/sessions` | — | Browse past session summaries |
| `/learn` | — | Extract reusable pattern into skills/ |

### Agent Roster

| Agent | Model | Purpose |
|-------|-------|---------|
| planner | Sonnet | Implementation planning; waits for confirmation |
| tdd-guide | Sonnet | Test-driven development; enforces RED → GREEN → REFACTOR |
| code-reviewer | Sonnet | Security + quality review |
| architect | Sonnet | System design; when planner escalates |
| security-reviewer | Sonnet | Deep vulnerability analysis |
| build-error-resolver | Sonnet | Minimal diffs to fix build/type errors |
| database-reviewer | Sonnet | PostgreSQL optimization + schema review |
| e2e-runner | Sonnet | Playwright E2E test generation + execution |
| refactor-cleaner | Sonnet | Dead code removal + consolidation |
| harness-optimizer | Sonnet | Agent reliability + cost audit |

### Development Loop

```
Explore (optional) → /plan → confirm → [fresh context] → /tdd ISSUE-ID
  → RED → GREEN → REFACTOR → commit → (repeat for each phase)
  → /code-review → address issues → gh pr create → CI → merge
  → /handoff → next ticket
```
