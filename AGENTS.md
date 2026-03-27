# AGENTS.md — Development Workflow

> Authoritative operating guide for Codex in this project.
> Read this entirely before taking any action on any task.
> Last updated: 2026-02-26

---

## PROJECT SETUP — Fill This In First

> When you copy this template into a new project, complete this section before anything else.
> Delete this block once filled in.

```
Project name: [NAME]
Issue tracker: [GitHub Issues / Linear / none]
Issue tracker URL: [URL or n/a]

Issue tracker setup:
  Create .Codex/project.json (gitignored — each developer sets their own):

    GitHub:
      { "tracker": "github" }
      { "tracker": "github", "githubRepo": "owner/repo" }   # optional: pin a specific repo
                                                              # omit to infer from git remote

    Linear:
      { "tracker": "linear", "linearTeam": "ENG" }
      { "tracker": "linear", "linearTeam": "ENG", "linearProject": "Q1 2026" }  # optional: assign to a project
                                                                                  # omit to create unassigned

    Neither:
      { "tracker": "none" }

  GitHub:  gh auth login
  Linear:  brew tap joa23/linear-cli https://github.com/joa23/linear-cli
           brew install linear-cli
           linear auth login
           linear init   # creates .linear.yaml with team + project defaults

Tech stack:
  Language:   [TypeScript / Python / Go / other]
  Frontend:   [Next.js / React / Vue / none]
  Backend:    [Next.js API / Express / FastAPI / other]
  Database:   [Postgres / SQLite / MongoDB / other]
  Auth:       [provider or custom]
  Deployment: [Vercel / Railway / Fly / other]

Default model: Codex Sonnet 4.6
Escalate to Opus for: [complex architecture decisions / large refactors / your call]

Skill files relevant to this project:
  - ./skills/[relevant]/SKILL.md

Build journal setup:
  Place BUILDING-SETUP.md in your project root (already included in this template), then say:
  "Read BUILDING-SETUP.md and follow the instructions"
  This creates a self-updating BUILDING.md — origin story, architecture decisions, build log.
  Run this once, right after filling in this PROJECT SETUP section.

Optional design plugin (for design system consistency across sessions):
  - Install: /plugin marketplace add Dammyjay93/interface-design
  - Creates: .interface-design/system.md (auto-loaded each session)
  - Commands: /interface-design:status, /interface-design:audit, /interface-design:extract
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

**Skill scope:** Skills are opt-in, not opt-out. Only reference skill files from `./skills/` that correspond to technologies declared in §4 (Tech Stack table). To identify relevant skills, read `./skills/INDEX.md` — do not browse the skills/ directory directly. Skills listed under a different stack in INDEX.md (Swift, Java, Go, Python, C++) are not applicable unless that stack appears in §4.

---

## 1. Core Development Loop

Every feature follows this sequence. **Never skip or combine steps — but you may start at Explore.**

```
EXPLORE (optional) → PLAN → ISSUES → IMPLEMENT (fresh context) → REVIEW
      ↓                ↓       ↓             ↓                       ↓
 free-form chat      /plan  tracker       /tdd                 /code-review
 no code written    planner  template    tdd-guide            code-reviewer
                    agent               agent                security-reviewer
```

### Step 0 — Explore (when the idea is fuzzy)

**When:** You have a vague concept, competing approaches, or unclear requirements
**Mode:** Free-form conversation — no commands, no agents, no code written
**Output:** Enough clarity to write a focused plan

Rules for exploration mode:
- Codex acts as a **thinking partner**, not an executor
- Ask questions, compare approaches, sketch trade-offs in plain language
- No files are created or edited during exploration
- No issue is opened until you have a clear direction
- End exploration with: *"I think I know what I want — let's plan it."*

Useful exploration prompts:
```
I'm thinking about [idea]. What are the different ways to approach this?
What are the trade-offs between [option A] and [option B] for this use case?
What questions should I be answering before I commit to building this?
What's the simplest version of this that would be worth shipping?
```

Exit exploration when you can answer: *What is the one thing this feature does, and how will I know it's working?*

### Step 1 — Plan

**When:** Idea is clear enough to plan
**Command:** `/plan`
**Agent invoked:** `planner` (Sonnet)
**Output:** Confirmed phased implementation plan with file paths and dependencies

Required behaviors:
- End every planning prompt with: *"Ask me any clarifying questions you might have."*
- The planner agent will **wait for your explicit confirmation** before touching any code
- Map architecture first: what does it do, how does it connect, how does data flow
- Identify dependencies and phase sequencing before committing
- Do NOT start implementing during planning

### Step 2 — Break into Issues

**When:** Plan is confirmed
**Mode:** Same planning context
**Output:** Issues created in your configured tracker, each independently shippable + `.ai/tickets/` context files written

After you confirm each plan, the planner automatically:
1. Creates the issue in your tracker via `gh issue create` (GitHub) or `linear issues create` (Linear)
2. Writes `.ai/tickets/{ISSUE-ID}/context.md` with the confirmed plan, files to read, and handoff state
3. Sets the active ticket pointer

Requires `.Codex/project.json` with your tracker config (see §0 PROJECT SETUP).

Each issue MUST be:
- **Single-scope**: One thing, done completely
- **Independently shippable**: Could be merged without the others
- **Sequenced**: References what comes before and after
- **Definition of Done**: Explicit, testable acceptance criteria

Use the Issue Template in §8 as the body template.

### Step 3 — Implement

**When:** Issues are created
**Mode:** **New chat session — non-negotiable**
**Command:** `/tdd GH-42` or `/tdd ENG-42`
**Agent invoked:** `tdd-guide` (Sonnet)
**Output:** Working code + passing tests (RED→GREEN→COMMIT→REFACTOR)

Required behaviors:
- Start EVERY implementation in a fresh context
- Use `/tdd ISSUE-ID` — one command loads the issue from the tracker, reads the ticket context, creates the feature branch (`feature/GH-42-title-slug`), and starts TDD
- Never implement multiple issues in one context session
- TDD cycle: write failing test → implement minimal code → **commit after GREEN** → refactor → verify coverage
- Commit format: `feat: add X` / `fix: resolve Y` (conventional commits) with issue reference in body

### Step 4 — Review

**When:** Implementation complete, tests passing
**Commands (in this order):**
1. `/code-review` — runs `code-reviewer` agent (confidence-filtered, 80%+ threshold)
2. Address all CRITICAL and HIGH issues surfaced
3. Optionally: run `security-reviewer` agent if touching auth, data access, or APIs
4. Verify the 3 comprehensibility checkpoints (§3)
5. Open PR: `gh pr create --title "..." --body "Closes #N\n\n..."` (see PR Description Template §8)
6. PR hook logs the URL automatically after creation

---

## 2. Context Management

Context window = a finite resource. Manage it deliberately.

### `/compact` vs `/clear` — know the difference

| Command | What it does | When to use |
|---------|-------------|-------------|
| `/compact` | Summarizes context, keeps continuity | Phase transitions within a task |
| `/clear` | Full wipe, fresh start | Unrelated new task |

**When to `/compact`** (at logical phase boundaries):

| Phase transition | Compact? | Reason |
|----------------|----------|--------|
| Research → Planning | Yes | Research is bulky; the plan is the distilled output |
| Planning → Implementation | Yes | Plan is in the issue; free context for code |
| Debugging → Next feature | Yes | Debug traces pollute new work |
| After a failed approach | Yes | Clear dead-end reasoning before trying again |
| Mid-implementation | No | Losing variable names and state is costly |
| Implementation → Testing | Maybe | Keep if tests reference recent code closely |

**What survives compaction:** AGENTS.md, TodoWrite task list, git state, all files on disk
**What's lost:** previously read file contents, conversation history, verbally stated preferences, tool call counts

### The Rules

| Rule | Trigger |
|------|---------|
| One task, one context | Never implement multiple features in the same session |
| Reset after planning | Start a new chat (or `/compact`) before implementation |
| Clear after completion | `/clear` before an unrelated next task |
| Externalize before clearing | Document decisions in the issue before resetting |
| 50+ messages = warning | Context degradation likely; `/compact` or recover |

### Context Recovery Pattern

When resuming after a reset, session summaries are loaded automatically by the SessionStart hook. If recovering manually:

```
I'm continuing work on [feature]. Issue: [link or ID].
Previously completed: [from session summary or issue comment].
Current state: [where we left off].
Continue from here.
```

Use `/checkpoint` to create a named git snapshot before clearing context.
Use `/sessions` to browse previous session summaries.

### Two-Layer System

**Strategic Layer — Issue Tracker**
- What to build: planning, acceptance criteria, sequencing
- Comments capture: planned → actual → learned
- Source of truth for *what*

**Tactical Layer — TodoWrite + Checkpoints**
- **TodoWrite** (Codex's native task list): current-session task breakdown — zero friction, visible in the UI, no file to manage
- **`/checkpoint`**: named git snapshots with a log at `.Codex/checkpoints.log` — cross-session progress record
- **Session files**: auto-created at `~/.Codex/sessions/` by the SessionEnd hook — no manual writes needed

**Workflow integration:**
1. Plan feature → issue in tracker
2. Break into sub-tasks → TodoWrite (ask Codex: *"Add these tasks to your task list"*)
3. Codex works; run `/checkpoint` at meaningful milestones
4. Session summary saved automatically when context ends
5. Next session: summary loaded automatically; run `/sessions` to review if needed
6. After implementation → post provenance comment on issue (template §8)

---

## 3. Code Standards

### Comprehensible Code

Before merging ANY PR, answer these three questions. If any is "no," do not merge.

1. Can I explain what this feature does and how it fits into the system?
2. Do I understand how the pieces connect — what calls what, how data flows?
3. If this breaks at 2am, do I know the entry points to start investigating?

If any answer is "no": run `/code-review` again, ask the `code-reviewer` agent to explain the architecture.

### Atomic Features

A PR is **not atomic** when any of these are true:
- 20+ files changed
- PR description requires more than 1-2 bullet points
- You feel nervous merging ("a lot could break")
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
- User-facing code: friendly messages; server-side: detailed logs

**Input Validation**
- Validate ALL user input at system boundaries
- Use schema-based validation (e.g., Zod, Yup, Pydantic, Joi — whatever fits the stack)
- Never trust external data (API responses, user input, file content)

**Code Quality Checklist** (run before marking work complete):
- [ ] Code is readable and well-named
- [ ] Functions are small (< 50 lines)
- [ ] Files are focused (< 800 lines)
- [ ] No deep nesting (> 4 levels) — use early returns
- [ ] Proper error handling at every level
- [ ] No hardcoded values (use constants or config)
- [ ] No mutation (immutable patterns used)

### Emergent Abstractions

Abstract only when you feel **real pain**, not anticipated pain:

| Real Pain → Abstract Now | Anticipated Pain → Wait |
|--------------------------|-------------------------|
| "I've written this same code 3 times" | "I might need this again someday" |
| "A bug fix requires changes in 5 places" | "This could get complicated later" |
| "I can't understand my own code" | "Someone might not understand this" |

**Prompts to hold the line:**
```
Let's keep this simple for now. Just implement the straightforward version — we can refactor later if needed.
```
```
I know this duplicates code from [file]. That's intentional — duplication over premature abstraction.
```

### No Overengineering

Only make changes that are directly requested or clearly necessary:
- Do NOT add features, refactor, or "improve" beyond what was requested
- Do NOT add docstrings, comments, or type annotations to code you didn't change
- Do NOT add error handling for scenarios that cannot happen
- Do NOT create helpers or abstractions for one-time operations
- Do NOT design for hypothetical future requirements

### Testing Requirements

**Minimum Coverage: 80%**
**100% required for:** financial calculations, authentication logic, security-critical code, core business logic

**TDD workflow** (mandatory — use `/tdd` command):
1. Write failing test first (RED)
2. Run test — verify it fails
3. Implement minimal code (GREEN)
4. Run test — verify it passes
5. Refactor (IMPROVE)
6. Verify coverage target met

**Test types required** for each feature:
- **Unit tests**: Individual functions, utilities, components
- **Integration tests**: API endpoints, database operations
- **E2E tests**: Critical user flows (use `/e2e` command)

---

## 4. Tech Stack

> **Fill in for this project.** Delete rows that don't apply. Add rows for your stack.

| Layer | Technology | Reference Skill |
|-------|------------|-----------------|
| Language | [TypeScript / Python / Go / other] | `./skills/coding-standards/SKILL.md` |
| Frontend | [Next.js / React / Vue / none] | `./skills/frontend-patterns/SKILL.md`, `./skills/react-best-practices/SKILL.md`, `./skills/composition-patterns/SKILL.md` |
| UI/Design | [shadcn / MUI / custom / none] | `./skills/web-design-guidelines/SKILL.md` |
| Styling | [Tailwind / CSS Modules / styled-components] | — |
| Backend | [Next.js API / Express / FastAPI / other] | `./skills/backend-patterns/SKILL.md` |
| Database | [Postgres / SQLite / MongoDB / other] | `./skills/database-migrations/SKILL.md` |
| Auth | [provider or custom] | — |
| Storage | [provider or custom] | — |
| AI | [Anthropic SDK / OpenAI / other] | — |
| Deployment | [Vercel / Railway / Fly / other] | `./skills/deployment-patterns/SKILL.md` |

**Stack-specific rules** (fill in based on your choices):
```
[e.g., "Enable Row Level Security on all tables if using Supabase"]
[e.g., "All API routes must use middleware X"]
[e.g., "Database migrations via [tool]"]
```

**When to deviate from defaults:**
- [Define conditions here for your project]

---

## 5. Agent Dispatch Table

Use specialized agents proactively — not only when you're stuck. Launch agents without waiting for user prompts when conditions below are met.

**Automatic agent dispatch rules:**

| Condition | Agent to Use | How to Invoke |
|-----------|-------------|---------------|
| Idea needs clarity before planning | Free-form chat (Step 0) | No command — just talk |
| New feature request or complex refactor | `planner` (Sonnet) | `/plan` |
| Architectural decision needed | `architect` (Sonnet) | `/plan` with architecture framing |
| Code just written or modified | `code-reviewer` (Sonnet) | `/code-review` |
| Bug fix or new feature | `tdd-guide` (Sonnet) | `/tdd` |
| Security-sensitive change | `security-reviewer` (Sonnet) | Direct invocation |
| Build or type errors | `build-error-resolver` (Sonnet) | `/build-fix` |
| Critical user flow needs testing | `e2e-runner` (Sonnet) | `/e2e` |
| Dead code cleanup needed | `refactor-cleaner` (Sonnet) | `/refactor-clean` |
| Schema design or query optimization | `database-reviewer` (Sonnet) | Direct invocation |

**Parallel agent execution**: When tasks are independent, launch multiple agents simultaneously. Example: security review + code quality review can run in parallel on the same PR.

**Multi-perspective analysis**: For complex problems, invoke multiple agents for competing perspectives:
```
Here's the code [agent 1] wrote. Review it critically. What could go wrong? What would you do differently?
```

**All agent definitions**: `.Codex/agents/`

---

## 6. Model Selection

**Default: Codex Sonnet 4.6** — use for all planning, implementation, and review tasks.

Escalate to **Codex Opus 4.6** only when:
- Architectural decisions with significant long-term consequences
- Debugging a complex multi-system failure with no clear entry point
- Reviewing a large multi-file refactor where missing a subtle dependency could cause a regression

Do not use Opus by default. The cost and latency aren't worth it for routine work. If Sonnet gets stuck, try a clearer prompt before escalating.

**Other models**: If your workflow includes other AI tools, define them here:
```
[Model / tool] → [specific use case in this project]
```

### CLI over MCP

Prefer CLI-wrapper commands over MCP servers for external tools:
- Use `gh` CLI via `/issue` and `/plan` — not a GitHub MCP server
- Use `linear` CLI via `/issue` and `/plan` — not Linear's MCP
- Use Supabase CLI, Railway CLI, etc. directly via Bash

CLI wrappers are lighter (no MCP config, no auth setup in Codex settings), don't consume context window, and are easier to debug. Use MCP only when a tool has no usable CLI.

---

## 7. Git Conventions

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/description` | `feature/user-dashboard` |
| Bug fix | `fix/description` | `fix/login-redirect` |
| Refactor | `refactor/description` | `refactor/api-client` |
| Experiment | `experiment/description` | `experiment/new-layout` |
| Spike | `spike/description` | `spike/auth-options` |

Rules: lowercase, hyphenated, no spaces, under 40 chars.

### Commit Messages

Use **conventional commits** format: `<type>: <description>`

```
feat: add user dashboard layout
fix: resolve redirect loop on login
refactor: extract API client to SDK
test: add unit tests for auth flow
docs: update deployment guide
chore: upgrade dependencies
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`

Include an issue reference in the commit body:
- GitHub: `Closes #42` (auto-closes the issue when the PR merges)
- Linear: `ENG-42` (Linear auto-links via branch name and commit body)

```
feat: add notification bell component

Closes #42
```

Never: `WIP`, `fix`, `updates`, `changes`, bare verbs without a type prefix

### When to Commit

- After each RED→GREEN cycle (tests pass) — before starting REFACTOR
- Before a context reset (`/checkpoint`)
- Never commit failing tests or a broken build

### PR Standards

- **Size**: < 400 lines changed
- **Description**: What + Why + How to test + Risks
- **CI**: Must pass before merging — never bypass with `--no-verify`
- **Review**: Respond to all comments before merging
- **Cleanup**: Delete branch after merge

### Risky Git Operations — Confirm Before Proceeding

Do not take these actions without explicit user confirmation:
- `git push --force` or `git push --force-with-lease`
- `git reset --hard`
- Deleting branches that may contain uncommitted work
- Amending published commits

When in doubt: investigate the state first; never discard work that might be in-progress.

---

## 8. Templates

### Issue Template

```markdown
## Summary
[1-2 sentences describing what this issue accomplishes]

## Context
[Why this matters / what it enables / how it fits into the larger feature]

## Requirements
- [ ] [Specific requirement 1]
- [ ] [Specific requirement 2]

## Technical Notes
[Implementation details, constraints, existing patterns to follow, relevant skill files]

## Dependencies
- Blocked by: [issue] (if applicable)
- Blocks: [issue] (if applicable)

## Definition of Done
- [ ] Feature works as described
- [ ] Tests written (TDD: RED→GREEN→REFACTOR), 80%+ coverage
- [ ] Code is comprehensible (can explain architecture)
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
[Brief explanation of approach, if not obvious]

## Testing
- [ ] TDD applied (tests written first)
- [ ] Unit tests: [describe]
- [ ] Integration tests: [describe]
- [ ] E2E tests: [describe if applicable]
- [ ] Tested on mobile (if UI change)

## Review
- [ ] `/code-review` passed — no CRITICAL/HIGH issues
- [ ] Security checklist cleared (§9)
- [ ] Comprehensibility checkpoints passed (§3)

## Risks
[What could go wrong? What should reviewers watch for?]
```

### Provenance Comment (post to issue tracker after implementation)

```
Summarize what we implemented:
- What was planned vs. what was actually built
- Any divergences from the plan and why
- What we learned or discovered during implementation

Format as a comment for [issue link].
```

---

## 9. Security Checklist

Security issues found? **STOP immediately, use `security-reviewer` agent, fix CRITICAL issues before continuing, rotate any exposed secrets.**

**Before ANY commit:**
- [ ] No hardcoded API keys, secrets, passwords, or tokens — use environment variables
- [ ] All user inputs validated with schema validation at system boundaries
- [ ] SQL injection prevented — parameterized queries only, no string concatenation
- [ ] XSS prevented — sanitize all user content before rendering
- [ ] CSRF protection enabled on state-changing endpoints
- [ ] Authentication/authorization verified on all protected routes
- [ ] Rate limiting on all public endpoints
- [ ] Error messages don't leak internal details to clients
- [ ] `console.log` / debug statements don't log sensitive data (tokens, passwords, PII)
- [ ] Commented-out code removed
- [ ] Database access controlled at the database level (RLS, permissions, or equivalent)
- [ ] Input validation present at all system boundaries (not just the frontend)

**Security Response Protocol:**
1. STOP immediately on discovery
2. Invoke `security-reviewer` agent
3. Fix all CRITICAL issues before proceeding
4. Rotate any exposed secrets
5. Review rest of codebase for similar patterns

---

## 10. Prompting Patterns

### Start Exploring (fuzzy idea)
```
I have a rough idea about [thing]. I'm not ready to plan yet — just help me think through it.
What are the main approaches? What questions should I answer before committing to one?
```

### Start Planning (idea is clear)
```
I want to build [feature]. Let me explain what I'm thinking...
[describe in natural language]
Ask me any clarifying questions you might have.
```

### Force Clarification
```
Before we proceed: what assumptions are you making? What should I answer first?
```

### Generate Issues from Plan
```
Break this plan into atomic issues. Each should be:
- Single-scope (one thing, done completely)
- Independently shippable
- Sequenced with dependencies noted
- Clear definition of done
```

### Start Clean Implementation
```
/tdd GH-42
```
or for Linear:
```
/tdd ENG-42
```
This loads the issue from the tracker, reads the ticket context, creates the feature branch, and starts TDD — all in one command.

### Prevent Scope Creep
```
Let's keep this PR focused on [specific thing]. [Other thing] is a separate issue.
```

### Learn From Code
```
Explain how this code works. I want to be able to write something similar myself.
```

### Pre-Merge Self-Check
```
Before I merge: does this do what [issue] asked for? Any obvious bugs or edge cases? Security concerns?
```

### Screenshot → Prompt (when words fail for UI work)
1. Screenshot the reference UI
2. Ask: "Describe this in terms of UX, components, and layout"
3. Edit the description to match your actual target
4. Use that description as your implementation prompt

---

## 11. Edge Cases & Deviations

### When to stay in exploration mode longer
**Condition**: Multiple valid approaches exist with meaningfully different trade-offs
**Rule**: Don't plan until you've compared the approaches and made a deliberate choice. A rushed plan produces the wrong issues.

### When NOT to reset context mid-task
**Condition**: Debugging something that emerged *during* implementation — you need the debugging history
**Rule**: Stay in context until the issue is resolved, then clear and continue clean

### When NOT to be atomic
**Condition**: Initial project scaffolding from scratch
**Rule**: Setup is inherently multi-scope. Once past initial setup, immediately return to atomic PRs.

### When to write code without a formal plan
**Condition**: Spike or proof-of-concept to answer a specific technical question
**Rule**: Use a `spike/` branch. Write throwaway code. Answer the question. Delete the branch. Then plan properly.

### Handling merge conflicts
1. Do NOT discard unfamiliar changes — investigate first
2. Understand both versions before resolving
3. Coordinate with other contributors if needed
4. Commit clearly: `chore: resolve merge conflict in [file]`

---

## 12. Anti-Patterns & Red Flags

If you observe any of these, stop and address before continuing.

| Signal | Problem | Fix |
|--------|---------|-----|
| "I can't explain this code" | Shipping slop | Ask `code-reviewer` for architecture explanation before merging |
| 50+ messages in context | Context degradation | Run `/checkpoint`, clear, recover |
| Codex referencing outdated ideas | Stale context | Externalize plan to issue, reset |
| PR touches 20+ files | Scope creep | Split into atomic issues |
| "This might break things" | Too much bundled | Ship smaller; don't merge what you can't debug |
| Abstraction before 3 instances of pain | Premature architecture | Revert to simple |
| "We might need this later" | Speculative feature | Only build what was asked |
| Implementing before reading the issue | Misaligned execution | Read the issue + affected files first |
| Planning when you're still fuzzy | Premature commitment | Go back to Explore (Step 0) |
| Using `--no-verify` | Bypassing quality gates | Fix the underlying issue |
| Deleting files/branches without investigation | Destroying in-progress work | Investigate; confirm with user |
| Making claims about code not read | Hallucination | Read the file before making any claims |
| Tests written after implementation | TDD violation | Delete implementation, restart with test first |

---

## 13. Hooks (Automatic Quality Gates)

These hooks run automatically via `.Codex/settings.json`. They enforce standards silently in the background.

| Hook | Trigger | What It Does |
|------|---------|-------------|
| Git push reminder | PreToolUse/Bash | Reminds to review changes before pushing |
| Doc file warning | PreToolUse/Write | Warns about non-standard `.md`/`.txt` files |
| Compact suggestion | PreToolUse/Edit\|Write | Suggests `/compact` every 25 tool calls past threshold of 50 |
| PR logger | PostToolUse/Bash | Logs PR URL + review command after `gh pr create` |
| Auto-format | PostToolUse/Edit | Formats JS/TS on save — detects Biome or Prettier; silent if neither found |
| Type check | PostToolUse/Edit | Runs `tsc --noEmit` on `.ts/.tsx` edits; reports errors for the edited file only |
| console.log warning | PostToolUse/Edit | Warns with line numbers when `console.log` added to JS/TS files |
| console.log scan | Stop | Scans all git-modified JS/TS files for `console.log` after each response |
| Session start | SessionStart | Auto-loads previous session summary into context |
| Session end | Stop | Auto-saves session summary to `~/.Codex/sessions/` |
| Pre-compact | PreCompact | Logs compaction event; marks active session file |

**Hook behavior**: Exit code `2` blocks the action. Exit code `0` allows with optional warning. All hooks log to stderr.
**Scripts**: All hook scripts live in `scripts/hooks/` with shared utilities in `scripts/lib/`.

---

## 14. Available Commands

Agent and command `.md` files live in `.Codex/agents/` and `.Codex/commands/`.

| Command | What It Does | When to Use |
|---------|-------------|-------------|
| `/plan` | Phased plan with file paths; auto-creates issue in tracker + writes ticket context after confirmation | After exploration, before implementing |
| `/tdd GH-42` | Load issue from tracker + ticket context + create branch, then implement with TDD | Start of every implementation session |
| `/tdd ENG-42` | Same as above for Linear issues | Start of every implementation session |
| `/tdd` | Continue active ticket (no arg = reads `.ai/tickets/active.md`) | Resuming in-progress work |
| `/issue list` | List open issues in configured tracker (GitHub or Linear) | Picking the next thing to work on |
| `/issue create` | Create an issue interactively in configured tracker | Before or after `/plan` |
| `/issue view 42` | View issue details from tracker | Checking issue body or status |
| `/issue close 42` | Close an issue in tracker | After PR merges |
| `/code-review` | Code quality + security review (80%+ confidence threshold) | After implementing, before PR |
| `/e2e` | Generate + run E2E tests via Playwright | Critical user flows |
| `/build-fix` | Fix build/type errors with minimal diff | When build fails |
| `/verify` | Verification loop — run, observe, fix | After implementation to confirm correctness |
| `/checkpoint` | Named git snapshot + log entry before context reset | At meaningful milestones |
| `/sessions` | Browse, load, and alias past session summaries | Resuming after a context clear |
| `/ticket GH-N` | Load ticket context, set as active ticket | When you have an ID but no arg on `/tdd` |
| `/handoff` | Write cross-agent handoff to active ticket context | Before ending session or switching agents |
| `/learn` | Extract a reusable pattern from this session into `~/.Codex/skills/learned/` | After solving a non-trivial problem |
| `/skill-create` | Generate a skill file from git history or session patterns | When a project-specific pattern emerges |
| `/update-skills` | Regenerate `skills/INDEX.md` from disk | After manually adding skill folders |
| `/refactor-clean` | Dead code cleanup and extraction | Code maintenance |
| `BUILDING-SETUP.md` | Self-installing build journal wizard — say "Read BUILDING-SETUP.md and follow the instructions" | Once, at project start |

---

## 16. Ticket Context & Cross-Agent Handoffs

The `.ai/tickets/` directory enables seamless handoffs between AI agents and across sessions.

### What It Is

Each issue that goes through `/plan` gets a `.ai/tickets/{ISSUE-ID}/context.md` file. The issue ID comes from the real tracker — `GH-{N}` for GitHub, `ENG-42` for Linear. The file contains:
- **Confirmed Plan** — authoritative implementation steps (never re-plan this)
- **Files to Read Before Starting** — critical codebase context for implementers
- **Current State** — what's done, in progress, and blocked
- **Handoff Instructions** — the exact next action for the next session

### How It Works

**Planning (creates the context):**
1. Run `/plan` — planner agent creates the plan
2. Confirm the plan
3. Planner creates the issue in your tracker (`gh issue create` or `linear issues create`)
4. Planner writes `.ai/tickets/{ISSUE-ID}/context.md` and sets `active.md`
5. Status: `planning-complete`

**Implementing in Codex (reads the context):**
- `/tdd GH-42` or `/tdd ENG-42` — one command sets the active ticket, pulls the issue from the tracker, reads the context, creates the feature branch, and starts TDD
- Session-start hook auto-injects the active ticket context at session start
- Status updates happen automatically (Last Updated, Last Agent)

**Implementing in Gemini CLI:**
- GEMINI.md Startup Ritual (§2) requires reading the active ticket context
- `/tdd GH-42` in Gemini works the same way
- `/handoff` must be run before ending the Gemini session

**Ending a session:**
- Run `/handoff` to write the Current State narrative
- Hooks auto-update Last Updated and Last Agent metadata
- Next session (any agent) picks up exactly where you left off

### Commands

| Command | What It Does |
|---------|-------------|
| `/tdd GH-42` | Load issue + ticket context + create branch → start TDD (preferred) |
| `/ticket GH-N` | Load ticket context and set as active (without starting TDD) |
| `/ticket list` | List all ticket contexts with their status |
| `/ticket status` | Show the full active ticket context |
| `/handoff` | Write Current State and Handoff Instructions before ending session |

### Active Ticket

`.ai/tickets/active.md` is a gitignored pointer to the current ticket. The session-start hook reads it and injects the ticket context automatically. `/tdd ISSUE-ID` sets it automatically — you rarely need `/ticket GH-N` separately.

### Agent Independence

Agent bodies live in `.ai/agents/` (the source of truth). Platform-specific files are generated by `scripts/gen-agents.js`:
- `.Codex/agents/` — Codex (with Codex frontmatter)
- `.gemini/agents/` — Gemini CLI (with Gemini frontmatter and tool names)

When you edit an agent's instructions, edit `.ai/agents/{name}.md`, then run `node scripts/gen-agents.js` to regenerate both platform outputs.

---

## 15. Quick Reference

### Decision: What should I do right now?

```
Idea is fuzzy / not sure what to build?
  → Explore (Step 0) — talk it through first, no code

Idea is clear, ready to commit?
  → /plan → confirm → issues auto-created in tracker → new context → /tdd GH-42 → /code-review → gh pr create

Continuing existing feature in a new session?
  → /tdd GH-42  (loads issue + context + branch in one command)

PR ready?
  → /code-review → address CRITICAL/HIGH → verify comprehensibility → gh pr create

At a phase boundary (research done, planning done, debugging done)?
  → /compact → continue in same session with clean context

Context getting noisy (50+ messages) or switching to unrelated task?
  → /checkpoint → /clear → next session auto-loads summary → /sessions to review if needed

Something broke?
  → Don't reset — debug in current context → fix → THEN clear and continue

Build/type errors?
  → /build-fix

Unclear what to build?
  → Re-read issue → ask clarifying questions BEFORE writing any code

Security issue found?
  → STOP → security-reviewer agent → fix CRITICAL → rotate secrets → continue
```

### Skill Deep Dives (reference material)

> Update these paths to match the skills relevant to your project stack.

| Topic | Path |
|-------|------|
| TDD patterns | `./skills/tdd-workflow/SKILL.md` |
| Frontend | `./skills/frontend-patterns/SKILL.md` |
| Backend | `./skills/backend-patterns/SKILL.md` |
| Database | `./skills/database-migrations/SKILL.md` |
| Security review | `./skills/security-review/SKILL.md` |
| API design | `./skills/api-design/SKILL.md` |
| E2E testing | `./skills/e2e-testing/SKILL.md` |
| Coding standards | `./skills/coding-standards/SKILL.md` |
| Deployment | `./skills/deployment-patterns/SKILL.md` |
| Postgres patterns | `./skills/postgres-patterns/SKILL.md` |
| React performance | `./skills/react-best-practices/SKILL.md` |
| Component architecture | `./skills/composition-patterns/SKILL.md` |
| UI/accessibility audit | `./skills/web-design-guidelines/SKILL.md` |
