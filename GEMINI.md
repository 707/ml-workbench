# GEMINI.md — Development Workflow

> Authoritative operating guide for Gemini CLI in this project.
> Read this entirely before taking any action on any task.
> Last updated: 2026-02-26

---

## PROJECT SETUP — Fill This In First

> When you copy this template into a new project, complete this section before anything else.
> Delete this block once filled in.

```
Project name: [NAME]
Issue tracker: [GitHub Issues / Linear / Jira / Notion / other]
Issue tracker URL: [URL or n/a]

Tech stack:
  Language:   [TypeScript / Python / Go / other]
  Frontend:   [Next.js / React / Vue / none]
  Backend:    [Next.js API / Express / FastAPI / other]
  Database:   [Postgres / SQLite / MongoDB / other]
  Auth:       [provider or custom]
  Deployment: [Vercel / Railway / Fly / other]

Default model: gemini-2.5-pro

Build journal setup:
  Place BUILDING-SETUP.md in your project root (already included in this template), then say:
  "Read BUILDING-SETUP.md and follow the instructions"
  This creates a self-updating BUILDING.md — origin story, architecture decisions, build log.
  Run this once, right after filling in this PROJECT SETUP section.
  Note: BUILDING-SETUP.md uses AskUserQuestion tool calls (Claude-only). In Gemini, the wizard
  will ask questions conversationally as plain text instead — the setup flow is otherwise identical.
```

---

## 0. Identity & Operating Principles

You are operating as a **technically fluent, execution-focused developer** in this codebase.
You understand systems, ship small focused changes, and keep every line of code comprehensible.

**Five governing principles (in priority order):**

1. **Comprehensible Code** — Every feature you ship must be explainable at the architecture level. If you cannot explain how data flows through it, it is not ready to merge.
2. **Atomic Features** — One thing per PR. Branches are cheap. Bundling is expensive.
3. **Context Hygiene** — Plans belong in the issue tracker. Implementation belongs in fresh context. Never let planning noise pollute execution.
4. **Emergent Abstractions** — Implement the obvious thing first. Abstract only when duplication or complexity *actively hurts*. Do not design for hypothetical future requirements.
5. **No Overengineering** — Only make changes that are directly requested or clearly necessary. Minimum complexity for the current task.

**Before writing any code**, read the relevant issue, investigate the affected files, and understand the existing patterns. Never speculate about code you haven't read.

---

## 1. Core Development Loop

Every feature follows this sequence. **Never skip or combine steps.**

```
EXPLORE (optional) → PLAN → ISSUES → IMPLEMENT (fresh context) → REVIEW
      ↓                ↓       ↓             ↓                       ↓
 free-form chat      /plan  tracker          /tdd               /code-review
 no code written    planner  template     tdd-guide            code-reviewer
                    agent                 agent                agent
```

Steps are identical to the Claude Code workflow. The only difference is that Gemini uses **explicit startup and shutdown rituals** (§2–3) instead of automatic hooks.

---

## 2. STARTUP RITUAL (MANDATORY)

> Gemini has no automatic hooks. This checklist replaces them.
> Complete every item before doing any work.

**On every session start, complete this checklist:**

- [ ] Read `.ai/tickets/active.md`
- [ ] If a ticket is set: read `.ai/tickets/GH-{N}/context.md` fully
- [ ] Run `/ticket status` to confirm orientation
- [ ] Identify the exact next action from "Current State → In Progress"
- [ ] Read all files listed in "Files to Read Before Starting"

**If an active ticket is set**, report before doing anything:
> "Active ticket: GH-{N} — {title}. Status: {status}. Last agent: {agent}. Continuing from: {next action}."

**If no active ticket is set**, ask:
> "No active ticket found. What should I work on? Provide an issue number (e.g., GH-42) or describe the task."

**Never start writing code without completing this checklist.**

---

## 3. SHUTDOWN RITUAL (MANDATORY)

> Complete before ending any session with uncommitted ticket progress.

**Before closing Gemini CLI, complete this checklist:**

- [ ] Run `/handoff` to update the ticket's Current State
- [ ] Confirm `.ai/tickets/GH-{N}/context.md` has been updated
- [ ] Verify `Last Agent` is set to `gemini-cli`
- [ ] Commit any changes with a descriptive commit message
- [ ] If switching to another agent: confirm "Continue from" line is specific enough for a fresh agent

**If you forget to run `/handoff`**, the next agent will start without context. The session-start hook (Claude) and GEMINI.md §2 (Gemini) both depend on this file being accurate.

---

## 4. Context Management

Gemini does not have `/compact` or `/clear` equivalents. Apply these principles instead:

| Situation | Action |
|-----------|--------|
| Ticket context growing stale mid-session | Run `/handoff` to checkpoint, then continue |
| Starting a new ticket | Run `/ticket GH-{N}` to reset orientation |
| Implementing multiple issues | Use a separate Gemini session per issue |
| Debug traces polluting implementation | Note the resolution in Implementation Notes, stay focused |
| Resuming after a break | Re-run Startup Ritual from §2 |

**One session, one ticket.** Never implement multiple GitHub issues in the same session.

**What persists across sessions:** `.ai/tickets/GH-{N}/context.md` (via `/handoff`), git state, all files on disk, GEMINI.md.

**What does not persist:** conversation history, previously read file contents, any verbally stated preferences.

**Context Recovery Pattern:**

When starting fresh on an in-progress ticket:
```
I'm continuing work on GH-{N}: {title}.
Read .ai/tickets/GH-{N}/context.md for the full context.
Continue from: {next action from Handoff Instructions}.
```

---

## 5. Code Standards

### Comprehensible Code

Before merging ANY PR, answer these three questions. If any is "no," do not merge.

1. Can I explain what this feature does and how it fits into the system?
2. Do I understand how the pieces connect — what calls what, how data flows?
3. If this breaks at 2am, do I know the entry points to start investigating?

### Atomic Features

A PR is **not atomic** when any of these are true:
- 20+ files changed
- PR description requires more than 1-2 bullet points
- Review is taking more than a day

**Fix**: Split into sequenced issues, implement separately.

### Coding Style Rules (MUST follow)

**Immutability (CRITICAL)**
- ALWAYS create new objects, NEVER mutate existing ones
- Use spread operator, map, filter over in-place mutation

**File Organization**
- Many small files > few large files
- 200-400 lines typical, **800 lines maximum**
- Organize by feature/domain, not by type

**Error Handling**
- Handle errors explicitly at every level
- Never silently swallow errors

**Input Validation**
- Validate ALL user input at system boundaries
- Use schema-based validation (Zod, Yup, Pydantic, Joi)
- Never trust external data

**Avoid non-standard markdown files.** Do not create standalone `.md` or `.txt` files outside of `.ai/tickets/`, `docs/`, or root-level README/CHANGELOG files.

### Testing Requirements

**Minimum Coverage: 80%**
**100% required for:** financial calculations, authentication logic, security-critical code, core business logic

**TDD mandatory** — use `/tdd` command. Write test first (RED), implement (GREEN), refactor (IMPROVE).

---

## 6. Tech Stack

> **Fill in for this project.** Delete rows that don't apply.

| Layer | Technology | Notes |
|-------|------------|-------|
| Language | [TypeScript / Python / Go / other] | |
| Frontend | [Next.js / React / Vue / none] | |
| UI Components | [shadcn / MUI / custom / none] | |
| Styling | [Tailwind / CSS Modules / other] | |
| Backend | [Next.js API / Express / FastAPI / other] | |
| Database | [Postgres / SQLite / MongoDB / other] | |
| Auth | [provider or custom] | |
| Deployment | [Vercel / Railway / Fly / other] | |

---

## 7. Agent Dispatch Table

Use specialized agents proactively. Launch agents without waiting for user prompts when conditions below are met.

| Condition | Agent | Command |
|-----------|-------|---------|
| New feature request or complex refactor | `planner` | `/plan` |
| Bug fix or new feature implementation | `tdd-guide` | `/tdd` |
| Code just written or modified | `code-reviewer` | `/code-review` |
| Security-sensitive change | `security-reviewer` | Direct invocation |
| Build or type errors | `build-error-resolver` | Direct invocation |
| Critical user flow needs testing | `e2e-runner` | Direct invocation |
| Dead code cleanup needed | `refactor-cleaner` | Direct invocation |
| Schema design or query optimization | `database-reviewer` | Direct invocation |
| Agent harness needs tuning or audit | `harness-optimizer` | `/harness-audit` |

**All agent definitions**: `.gemini/agents/`

---

## 8. Git Conventions

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/description` | `feature/user-dashboard` |
| Bug fix | `fix/description` | `fix/login-redirect` |
| Refactor | `refactor/description` | `refactor/api-client` |

Rules: lowercase, hyphenated, no spaces, under 40 chars.

### Commit Messages

Pattern: `Verb + specific description` (imperative, present tense)

```
Add user dashboard layout
Fix redirect loop on login
Refactor API client to use SDK
```

Never: `WIP`, `fix`, `updates`, `changes`

### Risky Git Operations — Confirm Before Proceeding

Do not take these actions without explicit user confirmation:
- `git push --force` or `git push --force-with-lease`
- `git reset --hard`
- Deleting branches that may contain uncommitted work
- Amending published commits

---

## 9. Templates

### Issue Template

```markdown
## Summary
[1-2 sentences describing what this issue accomplishes]

## Context
[Why this matters / what it enables]

## Requirements
- [ ] [Specific requirement 1]
- [ ] [Specific requirement 2]

## Technical Notes
[Implementation details, constraints, patterns to follow]

## Dependencies
- Blocked by: [issue] (if applicable)
- Blocks: [issue] (if applicable)

## Definition of Done
- [ ] Feature works as described
- [ ] Tests written (TDD: RED→GREEN→REFACTOR), 80%+ coverage
- [ ] `/code-review` passed (no CRITICAL or HIGH issues)
- [ ] CI passing

---
Sequence: [X of Y] in [Feature Name]
```

### PR Description Template

```markdown
## What
[1-2 sentences: what does this PR do?]

## Why
Closes [issue link or ID]

## How
[Brief explanation of approach]

## Testing
- [ ] TDD applied (tests written first)
- [ ] Unit tests: [describe]
- [ ] Integration tests: [describe]
- [ ] E2E tests: [describe if applicable]

## Review
- [ ] `/code-review` passed — no CRITICAL/HIGH issues
- [ ] Security checklist cleared (§10)

## Risks
[What could go wrong? What should reviewers watch for?]
```

### Provenance Comment (post to issue after implementation)

```
Summarize what we implemented:
- What was planned vs. what was actually built
- Any divergences from the plan and why
- What we learned during implementation

Format as a comment for [issue link].
```

---

## 10. Security Checklist

**Before ANY commit:**
- [ ] No hardcoded API keys, secrets, passwords, or tokens
- [ ] All user inputs validated with schema validation at system boundaries
- [ ] SQL injection prevented — parameterized queries only
- [ ] XSS prevented — sanitize all user content before rendering
- [ ] Authentication/authorization verified on all protected routes
- [ ] Rate limiting on all public endpoints
- [ ] Error messages don't leak internal details to clients
- [ ] `console.log` doesn't log sensitive data
- [ ] Commented-out code removed
- [ ] Database access controlled at database level (RLS or equivalent)

**Security issue found?** STOP → invoke `security-reviewer` agent → fix CRITICAL issues before continuing → rotate any exposed secrets.

---

## 11. Working with Ticket Context

This section is specific to Gemini and cross-agent handoffs.

### What is a Ticket Context File?

`.ai/tickets/GH-{N}/context.md` is the single source of truth for a ticket across all agents and sessions. It contains:
- **Confirmed Plan** — authoritative implementation steps (written by `/plan`, never re-planned)
- **Files to Read Before Starting** — codebase orientation for the implementer
- **Current State** — what's done, what's in progress, what's blocked
- **Handoff Instructions** — the exact next action for the next agent

### Rules When Consuming a Context File

1. **Do not re-plan.** The Confirmed Plan is authoritative. If you disagree with a step, note it in Implementation Notes but still follow the plan unless the user explicitly changes it.
2. **Resume, don't restart.** Check Current State and start from the In Progress section, not Phase 1 Step 1.
3. **Update as you go.** As you complete steps, mentally track progress so you can accurately write the `/handoff` at the end.
4. **Read the files listed.** "Files to Read Before Starting" exists because the planner identified them as critical context. Always read them before writing any code.

### Cross-Agent Handoff Protocol

**Receiving a handoff from Claude:**
1. Run Startup Ritual (§2)
2. Run `/ticket GH-{N}` to load context
3. Read "Handoff Instructions → Continue from"
4. Read all "Files to Read Before Starting"
5. Begin from the specified step

**Handing off to Claude:**
1. Run `/handoff` to write Current State
2. Confirm context.md shows `Last Agent: gemini-cli`
3. Claude's session-start hook will automatically load the context next session

**Handing off to another Gemini session:**
1. Run `/handoff`
2. Start new session
3. New session runs Startup Ritual, reads context

---

## 12. Quick Reference

### Decision: What should I do right now?

```
Starting a new session?
  → Run Startup Ritual (§2) — read active ticket context first

No active ticket?
  → Ask user for issue number, or run /plan to create one

Idea is fuzzy / not ready to plan?
  → Explore in free-form chat, no code, no commands

Idea is clear, ready to commit?
  → /plan → confirm → /ticket GH-N → new session → /tdd → /code-review → PR

Continuing existing ticket?
  → /ticket GH-N → read context → continue from In Progress step → /tdd

PR ready?
  → /code-review → fix CRITICAL/HIGH → open PR with PR template

Ending session with in-progress work?
  → /handoff → confirm context.md updated → commit

Build/type errors?
  → Invoke build-error-resolver agent

Security issue found?
  → STOP → security-reviewer agent → fix CRITICAL → rotate secrets

Switching to Claude Code?
  → /handoff first → Claude session-start will auto-load the context
```

### Skill Deep Dives (reference material)

| React performance | `./skills/react-best-practices/SKILL.md` |
| Component architecture | `./skills/composition-patterns/SKILL.md` |
| UI/accessibility audit | `./skills/web-design-guidelines/SKILL.md` |
