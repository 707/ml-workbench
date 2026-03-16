# User Guide — AI Coding Workflow

> This guide explains how the system works and why each piece exists.
> For exhaustive reference, see `CLAUDE.md`. For Gemini CLI users, see `GEMINI.md`.

---

## The Problem This System Solves

AI coding assistants are powerful but undisciplined by default. Without structure, the same four problems appear in almost every project:

**1. Context pollution.** You plan a feature, ask questions, reject ideas, revise scope — then start implementing in the same session. Claude draws on all of that noise. It uses rejected approaches, references outdated decisions, and makes assumptions from things you said thirty messages ago.

**2. Scope creep.** "While I'm in here, let me also fix this." A login redirect fix ends up touching 25 files. The PR becomes unmergeable. You cannot tell what changed or why.

**3. Incomprehensible output.** Features that pass tests but nobody can explain. If it breaks at 2am, you have no idea where to start. The code works; it is not comprehensible.

**4. Lost context across sessions.** A debugging session surfaces exactly the right insight. The session ends. The next session starts from scratch. Claude re-learns the same things, makes the same detours.

```
Without this system:

  Planning ──► "let me just start coding" ──► scope creep
      |                                            |
  context gets stale                   PR touches 30 files
      |                                            |
  Claude uses stale assumptions        "I cannot explain this code"
      |                                            |
  Session ends ──► all context lost    Debugging: "just restart"
```

This system addresses each failure directly. Every piece of it exists to prevent one of these four problems.

---

## The Five-Step Loop

Every feature follows one loop. Never skip steps. Never combine them.

```
EXPLORE        PLAN          ISSUES        IMPLEMENT      REVIEW
(optional)
   |             |              |               |             |
free-form      /plan         GitHub /       NEW SESSION   /code-review
  chat         planner        Linear           /tdd         code-reviewer
  (no code)    agent         template          tdd-guide    security-reviewer
               (wait for     (atomic,          agent
               confirm)       sequenced)       (tests first)
                   |              |                |
                ticket         one issue =     fresh context
               context.md       one PR          per issue
```

| Step | What happens | Output | Failure mode it prevents |
|------|-------------|--------|--------------------------|
| **Explore** | Free-form thinking — no commands, no code | Clear direction | Premature planning from fuzzy ideas |
| **Plan** | `/plan` → phased plan → confirmation | Ticket context file | Wrong implementation, missed dependencies |
| **Issues** | Break plan into atomic issues | Sequenced tracker issues | Scope creep, unbounded PRs |
| **Implement** | New session, `/tdd`, test-first | Passing tests + code | Context pollution, TDD violations |
| **Review** | `/code-review` → PR | Approved, merged PR | Shipping incomprehensible or insecure code |

> **The most common mistake:** "I'll just keep going from here."
>
> Why this breaks: The planning session is full of 'what about...' discussions,
> rejected options, and uncertainty. The implementation session should contain
> only the confirmed plan — which now lives in the issue and in `.ai/tickets/`.
> A fresh context that reads only the issue produces better implementations.

---

## Getting Started

After copying this template into a new project, do four things:

1. **Fill in the PROJECT SETUP block in `CLAUDE.md`** — project name, tech stack, issue tracker URL. Delete the block once done.
2. **Fill in the same block in `GEMINI.md`** — only if you are using Gemini CLI.
3. **Set up your build journal** — say `"Read BUILDING-SETUP.md and follow the instructions"`. The wizard explores your project, asks 2-3 questions, and generates a personalized `BUILDING.md` that auto-updates as you build. Runs once at project start; the setup file deletes itself when done.
4. **Verify hooks are active** — open Claude Code in the project directory. The session-start hook should fire and confirm it loaded a previous session (or report no prior session on first use).

That is all. Hooks, agents, and commands are already configured.

```
project-template/
  CLAUDE.md            <- Fill in PROJECT SETUP first
  GEMINI.md            <- Fill in if using Gemini CLI
  USER-GUIDE.md        <- You are here
  BUILDING-SETUP.md    <- Run once: "Read BUILDING-SETUP.md and follow the instructions"
                          Self-installs as BUILDING.md (living build journal), then deletes itself
  .claude/
    agents/            <- 9 specialist agents (do not edit directly)
    commands/          <- 13 slash commands
    settings.json      <- 10 automatic hooks
  .ai/
    agents/            <- Agent source of truth (EDIT HERE)
    tickets/           <- Cross-agent handoff docs (auto-managed)
  scripts/
    hooks/             <- Hook scripts (called by settings.json)
    gen-agents.js      <- Regenerate agents after editing .ai/agents/
  skills/              <- Reference skill files for your stack
```

> **Gotcha — agent editing:** Edit `.ai/agents/{name}.md`, not `.claude/agents/{name}.md`.
> The `.claude/agents/` directory is generated by `scripts/gen-agents.js`.
> Changes made directly there will be overwritten the next time that script runs.

---

## Using the System Day-to-Day

### Step 0: Explore (When Your Idea Is Fuzzy)

Use when: you have a rough idea but are not sure what to build, or which approach to take. This step has no command and produces no code. It is a conversation.

```
"I'm thinking about adding a notification system. Not ready to plan yet —
 help me think through the approaches. What are the trade-offs?"

"What's the simplest version of this that would be worth shipping?"

"What questions should I answer before committing to one approach?"
```

**Exit condition:** You can answer — *"The one thing this feature does is X, and I will know it is working when Y."* If you cannot answer that, keep exploring.

Why this step exists: most bad plans come from committing too early. Exploration is free. Re-writing a mis-planned implementation is expensive.

---

### Step 1: Plan

**Command:** `/plan`

The `planner` agent reads your description, asks clarifying questions, maps the architecture, and presents a phased plan with specific file paths. It waits for your explicit confirmation before creating anything.

```
You:      /plan  Add Stripe subscription billing with three tiers.
                 Ask me any clarifying questions you might have.

planner:  [asks 2-3 clarifying questions about billing model, trial
           periods, existing auth setup]

You:      [answers]

planner:  [presents phased plan: schema, webhook handler, checkout
           route, pricing page, feature gating]
          Waiting for confirmation — proceed? (yes / no / modify)

You:      yes

planner:  Ticket context written to .ai/tickets/GH-42/context.md
          Active ticket set to GH-42.
          Start implementation with /tdd in a fresh session.
```

Always end planning prompts with: *"Ask me any clarifying questions you might have."* This prevents the planner from making assumptions you will have to undo in implementation.

After confirmation, the planner creates a ticket context file (covered in detail in [Ticket Context](#ticket-context-the-connective-tissue)) and sets the active ticket. This file is the handoff document that makes cross-session and cross-agent work possible.

---

### Step 2: Create Issues

Still in the same planning session. Ask Claude to break the confirmed plan into atomic issues.

```
"Break this plan into atomic issues. Each should be independently
 shippable and have a clear definition of done."
```

**After you confirm each issue:** Claude automatically creates it in your configured tracker and writes the `.ai/tickets/` context file. No manual copy-pasting required.

For this to work, create `.claude/project.json` in your project (gitignored — set it once per machine):

```json
// GitHub — infers repo from git remote
{ "tracker": "github" }

// GitHub — pin a specific repo (useful in monorepos or cross-org contributions)
{ "tracker": "github", "githubRepo": "owner/repo" }

// Linear — create unassigned issues in team ENG
{ "tracker": "linear", "linearTeam": "ENG" }

// Linear — assign issues to a specific project
{ "tracker": "linear", "linearTeam": "ENG", "linearProject": "Q1 2026" }

// No tracker — Claude asks for the issue number manually
{ "tracker": "none" }
```

**First-time tracker setup:**

```bash
# GitHub — authenticate with gh CLI
gh auth login

# Linear — install the CLI and authenticate
brew tap joa23/linear-cli https://github.com/joa23/linear-cli
brew install linear-cli
linear auth login
linear init    # creates .linear.yaml with your team + project defaults
```

You can also use `/issue create` to create issues manually before or independently of `/plan`.

What makes an issue atomic:

```
Good issue:                          Bad issue:
  One thing, done completely           "Add the whole billing system"
  Independently shippable              Cannot merge without the others
  Clear definition of done             "Make it work"
  Sequenced — lists dependencies       No sequencing
```

The implementation order follows their dependencies. `/plan` outputs the sequence.

---

### Step 3: Implement (New Session — Non-Negotiable)

**Start a new Claude Code session.** This is the hardest discipline to maintain and the most important one. Do not implement in the same session you planned in.

**First message — one command, loads everything:**
```
/tdd GH-42
// or
/tdd ENG-42
```

That single command does five things automatically:
1. Sets GH-42 (or ENG-42) as the active ticket
2. Reads `.ai/tickets/GH-42/context.md` (the confirmed plan)
3. Pulls the real issue body from GitHub (`gh issue view 42`) or Linear (`linear issues get ENG-42`)
4. Creates a feature branch: `feature/GH-42-{title-slug}` (if you're on `main`)
5. Reports where it's picking up from

If you're continuing an issue that's already active (set from a previous session), just run `/tdd` with no argument — it reads the active ticket automatically.

**The TDD cycle:**

```
  Write failing test (RED)
         |
         v
  Run test ──► confirm it fails
         |
         v
  Write minimal implementation (GREEN)
         |
         v
  Run test ──► confirm it passes
         |
         v
  Commit  ──► feat: add X\n\nCloses #42
         |
         v
  Refactor (IMPROVE)
         |
         v
  Run test ──► confirm still passes
         |
         v
  Coverage check (>= 80%)
         |
    [next behavior]
```

**Commit after each GREEN, before REFACTOR.** This keeps history clean and bisect-friendly.

**Commit format — conventional commits:**

```
feat: add notification bell component
fix: resolve redirect loop on login
refactor: extract notification service to lib/
test: add unit tests for auth flow
docs: update deployment guide
chore: upgrade dependencies
```

Types: `feat` (new feature), `fix` (bug fix), `refactor` (no behavior change), `test`, `docs`, `chore`, `perf`, `ci`

Always include the issue reference in the commit body — not the subject line:

```
feat: add notification bell component

Closes #42
```

For Linear: use `ENG-42` in the body. Linear auto-links commits via the branch name pattern `feature/ENG-42-*`.

The sequence matters: test first, then implementation. The test defines the interface. The implementation satisfies it. Reversing this order produces tests that rubber-stamp code rather than specifications that drive it.

**Coverage requirements:**

```
General code                80% minimum
Financial calculations      100%
Authentication logic        100%
Security-critical code      100%
Core business logic         100%
```

> **Gotcha:** If you wrote code before the test, delete the code and start with the test.
> This is not optional. Tests written after implementation are not TDD —
> they are documentation with extra steps, and they do not catch the bugs that matter.

---

### Step 4: Review

Run these in order before opening a PR:

1. **`/verify`** — runs build, type check, lint, tests, coverage, and console.log scan
2. **`/code-review`** — invokes the `code-reviewer` agent against the git diff
3. Address all **CRITICAL** and **HIGH** severity issues
4. (For auth, payment, user data, or API code) Invoke `security-reviewer` directly
5. Answer the three comprehensibility checkpoints — see below
6. Open PR via `gh pr create`:
   ```bash
   gh pr create \
     --title "feat: add notification bell" \
     --body "Closes #42

   ## What
   Add notification bell to the header...

   ## Testing
   - [x] TDD applied, tests pass
   - [x] Coverage 80%+"
   ```
   The PR logger hook captures the URL automatically after creation.

**Three comprehensibility checkpoints — answer before merging:**

```
1. Can I explain what this feature does and how it fits into the system?
2. Do I understand how the pieces connect: what calls what, how data flows?
3. If this breaks at 2am, do I know where to start investigating?

If any answer is "no" — do not merge.
Run /code-review again and ask the code-reviewer to explain the architecture.
```

**Severity levels from `code-reviewer`:**

```
CRITICAL   Must fix before merge. Security vulnerabilities, data loss risk.
HIGH       Should fix before merge. Missing error handling, oversized files.
MEDIUM     Address before final merge. Performance, best practices.
LOW        Nice to fix. Naming, documentation, minor style.
```

The `code-reviewer` only reports issues it is more than 80% confident are real problems. It consolidates related issues rather than flooding you. One finding — "five functions missing error handling in `src/api/`" — is more actionable than five separate findings.

---

## The Agents

The system has nine specialist agents. Each has a focused role with specific constraints. Think of them as team members: you would not ask your security engineer to refactor CSS, and you would not ask your TypeScript specialist to design the database schema.

**Why specialists instead of one general assistant:** A specialist agent has a focused system prompt that excludes everything outside its domain. The `build-error-resolver` only fixes errors — it does not refactor while it is in the file. The `refactor-cleaner` only removes dead code — it does not optimize anything it touches. Constraints produce better output than open-ended instructions.

```
Agent                 Command              When to Use
---------             -------              -----------
planner               /plan                New feature, complex refactor,
                                           architectural decision
tdd-guide             /tdd                 Implementing any feature or fix
code-reviewer         /code-review         After implementing, before PR
security-reviewer     (invoke directly)    Auth, payment, user data, APIs
build-error-resolver  /build-fix           Type errors, compilation failures
e2e-runner            /e2e                 Critical user flows
database-reviewer     (invoke directly)    Schema design, query optimization,
                                           Supabase RLS, migrations
refactor-cleaner      /refactor-clean      Dead code, unused exports, cleanup
architect             /plan (framed)       Major structural decisions,
                                           system design trade-offs
```

**planner** — Creates phased implementation plans with specific file paths, estimated complexity, and risk assessment. Waits for your explicit confirmation before touching anything. After confirmation, writes the ticket context file that all other agents use to orient themselves.

**tdd-guide** — Enforces RED→GREEN→REFACTOR. Its first action on every invocation is loading the active ticket context. It reads the confirmed plan and the listed context files before writing a single line of code. Never implements without understanding the plan.

**code-reviewer** — Reviews the git diff against a four-tier severity checklist (CRITICAL, HIGH, MEDIUM, LOW). Applies an 80%+ confidence threshold — it does not report stylistic preferences or uncertain observations. Produces a verdict: approve, warn, or block.

**security-reviewer** — Covers OWASP Top 10: injection, broken authentication, sensitive data exposure, XSS, insecure deserialization, and more. Also catches hardcoded secrets and insecure cryptography. When it finds a CRITICAL issue: stop, fix it, rotate any exposed secrets, then scan the rest of the codebase for the same pattern.

**build-error-resolver** — Fixes TypeScript and build errors with minimal diffs. It will not refactor, rename, optimize, or improve anything it touches. Its constraint is absolute: get the build green, nothing more. This is by design — fixing a build in the middle of an implementation is dangerous if the agent starts rewriting code.

**e2e-runner** — Generates and runs Playwright tests for complete user journeys. Uses Page Object Model for maintainability. Captures artifacts: screenshots, videos, and traces on failure. Quarantines flaky tests with recommendations rather than silently retrying.

**database-reviewer** — Covers PostgreSQL and Supabase: missing indexes, N+1 query patterns, schema design, Row Level Security (RLS) policies, connection management, and query performance. Use before merging any migration or query change.

**refactor-cleaner** — Runs knip, depcheck, and ts-prune to find dead code, unused exports, and unused dependencies. Categorizes findings as SAFE, CAUTION, or DANGER. Only deletes SAFE items — one at a time, running tests after each deletion to verify nothing broke.

**architect** — System-level design and trade-off analysis. Use for decisions with long-term consequences: data model choices, service boundaries, integration patterns, scalability considerations. Invoke via `/plan` with architecture framing, or directly.

> **Agents can run in parallel when their work is independent.**
> Running `security-reviewer` and `code-reviewer` on the same PR simultaneously
> is safe — they read the diff independently and their findings do not overlap.

---

## The Commands

Commands are the user-facing interface to agents and workflows. Most do more than their name suggests.

**`/plan`** — Invokes the `planner` agent. Always ends with the planner waiting for your confirmation before creating any files. After you confirm, it creates the issue in your configured tracker (`gh issue create` or `linear issues create`), writes the ticket context file, and sets the active ticket. The confirmation gate is intentional: it forces you to read and understand the plan before locking it in.

**`/tdd GH-42`** (or `/tdd ENG-42`) — The recommended way to start an implementation session. One command does five things: sets the active ticket, reads `.ai/tickets/GH-42/context.md`, pulls the real issue body from GitHub or Linear, creates the feature branch (`feature/GH-42-title-slug` if you're on `main`), and starts TDD. Use `/tdd` with no argument to continue the active ticket from a previous session.

**`/issue`** — Manage issues in your configured tracker without leaving Claude Code:
```
/issue list              list open issues
/issue create            create an issue interactively
/issue view 42           view issue title, body, labels (GH) or full details (Linear)
/issue close 42          close the issue (GH) or mark Done (Linear)
```
Uses `gh` or `linear` CLI based on `.claude/project.json`. Useful before `/plan` to draft the issue, or after a PR merges to close the issue.

**`/code-review`** — Invokes the `code-reviewer` agent against the current git diff (staged and unstaged). Run after every implementation, before every PR. Works on the actual diff, not hypothetical code.

**`/build-fix`** — Invokes the `build-error-resolver`. Use when `tsc` or the build fails. This agent has a hard constraint: it will not refactor, rename, or improve anything — only fix. If fixing a type error requires an architectural change, the agent will stop and tell you rather than making the change unilaterally.

**`/e2e`** — Invokes the `e2e-runner` for Playwright-based end-to-end tests. Use for critical user flows: authentication, payment checkout, core CRUD operations. Not required for every feature — use judgment based on risk and user impact.

**`/refactor-clean`** — Invokes the `refactor-cleaner`. Run during maintenance periods, not during active feature development. The agent runs analysis tools, categorizes findings by risk level, and removes only verified-safe dead code — one item at a time with test verification between each deletion.

**`/verify`** — Runs the full verification loop in order: build check → type check → lint → tests + coverage → console.log audit → git status. Use before marking a feature complete or opening a PR. Supports arguments:
```
/verify           runs everything (default)
/verify quick     build + types only
/verify pre-pr    full + security scan
```

**`/checkpoint`** — Creates a named git snapshot and logs it to `.claude/checkpoints.log`. Use before clearing context, before risky git operations, and at the end of significant phases.
```
/checkpoint create "auth-middleware-done"
/checkpoint list
/checkpoint verify "auth-middleware-done"   <- compare current state vs snapshot
```

**`/ticket`** — Loads a ticket context file and sets it as the active ticket. Most of the time you won't need this directly — `/tdd GH-42` handles it automatically. Use `/ticket` when you want to inspect or switch the active ticket without starting TDD:
```
/ticket GH-42        load and activate (without starting TDD)
/ticket list         show all tickets and their statuses
/ticket status       show the full active ticket context
/ticket clear        unset active ticket
```

**`/handoff`** — Updates the active ticket's context file with the current session's progress. Run this before ending any session with in-progress work, and before switching between Claude and Gemini. The "Continue from" line it writes must be specific enough for a fresh agent with no prior context to start immediately — not "continue with phase 2" but "Phase 2 Step 1: create the pricing page component at `src/app/pricing/page.tsx`."

**`/sessions`** — Browses and loads previous session summaries. Sessions are auto-saved by the session-end hook. Use this when returning to a project after a break.
```
/sessions              list all sessions
/sessions load <id>    display a specific session
/sessions alias <id> before-billing   create a memorable alias
```

**`/learn`** — Extracts a reusable pattern from the current session into `~/.claude/skills/learned/`. Use after solving a non-obvious problem: a tricky TypeScript pattern, an API quirk, a debugging technique that will recur. Asks for confirmation before saving.

**`/skill-create`** — Analyzes the git history to generate a `SKILL.md` file capturing the project's patterns: commit conventions, file co-change patterns, architecture decisions, testing patterns. Use early in a project to capture your conventions, and again after a major refactor.

**`BUILDING-SETUP.md`** — A one-time self-installing build journal wizard (not a slash command — trigger by saying `"Read BUILDING-SETUP.md and follow the instructions"`). It explores your project autonomously, asks 2-3 questions, and generates a personalized `BUILDING.md` that auto-updates as you build. The journal captures architecture decisions, build log entries, key learnings, and periodic check-ins. Works with both Claude Code and Gemini CLI (Gemini adapts the question flow to plain text instead of interactive prompts). The setup file deletes itself on completion — all that remains is your `BUILDING.md`.

**`/update-skills`** — Regenerates `skills/INDEX.md` from all skill folders on disk. Run after manually pasting, adding, or removing skill folders. The index is also regenerated automatically whenever Claude writes a `skills/*/SKILL.md` file, so this command is mainly needed after manual additions outside Claude Code.

---

## Skills and Stack Scope

The `skills/` directory contains 52+ reference skill files across multiple tech stacks (web/TypeScript, Python, Go, Java, Swift/iOS, C++, and more). **Skills are opt-in, not opt-out** — only skills matching your declared tech stack are relevant to your project.

**How to find the right skills:**
1. Check §4 (Tech Stack) of `CLAUDE.md` — the technologies listed there define your project's scope
2. Read `skills/INDEX.md` — the auto-generated index organized by stack
3. Only use skills from the matching section(s) in that index

Do not browse the `skills/` directory directly. Reading `skills/INDEX.md` first prevents the LLM from picking up skills for unrelated stacks (e.g., Swift skills on a web project).

**When you add a new skill:**
1. Create `skills/<skill-name>/SKILL.md` with `stack: <value>` in the frontmatter
2. Run `/update-skills` to regenerate the index
3. Valid stack values: `web`, `python`, `go`, `java`, `swift`, `cpp`, `database`, `general`

---

## Ticket Context: The Connective Tissue

The ticket context system is the least obvious piece of the workflow and the one that does the most invisible work. It solves the problem of continuity — across sessions, across agents, and across days.

**The problem without ticket context:**

```
Without ticket context:

  Session 1: Plan the feature. Confirm the approach.
  [End session]
  Session 2: "What was I building again? Let me re-read the issue..."
             [Re-discovers the plan, possibly makes different decisions]
  [Switch from Claude to Gemini]
  Gemini:    "I'll start from scratch since I don't know the context."
```

**With ticket context:**

```
Session 1: /plan -> confirm -> issue auto-created in GitHub/Linear
                            -> ticket context written to .ai/tickets/GH-42/
[End session]
Session 2: /tdd GH-42 -> loads issue from GitHub, reads .ai/tickets/GH-42/,
                         creates branch feature/GH-42-stripe-billing ->
           "Loaded GH-42: Stripe Billing. Resuming from Phase 2 Step 1."
[Switch to Gemini]
Gemini:    /tdd GH-42 -> same context, same branch, same plan.
```

The ticket ID (`GH-42` for GitHub, `ENG-42` for Linear) comes from the real tracker — `/plan` creates the issue automatically after you confirm the plan. The `.ai/tickets/` folder name matches that ID exactly.

**The ticket lifecycle:**

```
/plan confirmed
    |
    v
planner writes .ai/tickets/GH-42/context.md
    |
    v
.ai/tickets/active.md set to GH-42
    |
    v
[New session] session-start hook reads active.md
    ──► loads context.md automatically
    |
    v
/tdd reads context
    ──► knows the plan
    ──► knows which files to read before coding
    |
    v
Implementation work
    |
    v
/handoff (run before ending session)
    ──► updates Current State: what's done, what's in progress
    ──► writes specific "Continue from" instruction
    |
    v
[Next session or next agent] reads context -> continues from exact point
```

**What the context file contains:**

```
Status / Last Agent / Last Phase    metadata, auto-updated by hooks
Summary                             2 sentences: what and why
Confirmed Plan                      authoritative phases and steps
Files to Read Before Starting       critical codebase context
Current State                       completed / in-progress / blocked
Implementation Notes                decisions made, patterns chosen
Test Strategy                       unit / integration / E2E
Handoff Instructions                exact next action ("Continue from:")
```

The Confirmed Plan is authoritative. Once confirmed, it does not change unless you explicitly re-plan. If you discover a problem mid-implementation, note it in Implementation Notes and raise it with the user — do not silently deviate from the plan.

> **Gotcha:** Hooks auto-update timestamps and the Last Agent field in the metadata.
> But the narrative Current State update — what is done, what is in progress, what
> comes next — requires you to run `/handoff` explicitly. Hooks cannot write prose.
> If you end a session without running `/handoff`, the next session starts without
> knowing your progress.

**Cross-agent handoff (Claude ↔ Gemini):**

```
Claude -> Gemini:
  1. Run /handoff (writes Current State, marks Last Agent: claude-code)
  2. Gemini startup ritual reads .ai/tickets/active.md automatically

Gemini -> Claude:
  1. Run /handoff (marks Last Agent: gemini-cli)
  2. Claude session-start hook auto-loads the context on next session start

Both agents read from and write to the same .ai/tickets/ directory.
```

---

## Hooks: What Happens Automatically

Hooks enforce standards in the background without requiring you to remember to run anything. They are configured in `.claude/settings.json` and fire at specific lifecycle points.

The principle behind hooks: a developer who formats code manually will sometimes forget. A hook that formats on every edit never forgets. For anything that should happen *every single time*, a hook is more reliable than a habit.

| Hook | Trigger | What It Does |
|------|---------|-------------|
| Git push reminder | PreToolUse/Bash | Reminds to review changes before pushing |
| Doc file warning | PreToolUse/Write | Warns about non-standard `.md`/`.txt` files outside `docs/` |
| Compact suggestion | PreToolUse/Edit\|Write | Suggests `/compact` every 25 tool calls past threshold of 50 |
| PR logger | PostToolUse/Bash | Logs PR URL + review command after `gh pr create` |
| Auto-format | PostToolUse/Edit | Formats JS/TS on save — detects Biome or Prettier; silent if neither found |
| Type check | PostToolUse/Edit | Runs `tsc --noEmit` on `.ts/.tsx` edits; reports errors for the edited file only |
| console.log warning | PostToolUse/Edit | Warns with line numbers when `console.log` is added to JS/TS |
| Skills index update | PostToolUse/Write | Regenerates `skills/INDEX.md` when any `skills/*/SKILL.md` is written |
| console.log scan | Stop | Scans all git-modified JS/TS files for `console.log` after each response |
| Session end | Stop | Saves session summary to `~/.claude/sessions/`; updates ticket metadata |
| Session start | SessionStart | Loads previous session summary and active ticket context on startup |
| Pre-compact | PreCompact | Logs compaction event; marks active session file |

**How hook exit codes work:** A hook that exits with code `2` blocks the action entirely. A hook that exits with code `0` allows the action and optionally prints a warning. The TypeScript check uses code `0` — it reports errors without stopping Claude mid-edit.

---

## Session Continuity

Context windows are finite. Sessions end. People take breaks. This section explains how the system keeps work from disappearing.

**The two-layer model:**

```
Layer 1: Strategic (persists forever)
  Issue tracker         what to build, acceptance criteria, sequencing
  .ai/tickets/          confirmed plans, cross-agent handoffs, current state

Layer 2: Tactical (persists across sessions, auto-managed)
  ~/.claude/sessions/   automatic session summaries (saved by hooks)
  .claude/checkpoints.log  named git snapshots
  TodoWrite             current-session task breakdown (visible in Claude UI)
```

**What survives compaction or session end vs. what is lost:**

```
Survives /compact or session end:       Lost in /compact or session end:

  CLAUDE.md                               Conversation history
  TodoWrite task list                     Previously read file contents
  Git state and commits                   Verbally stated preferences
  .ai/tickets/ context files              Debug traces and detours
  Files on disk                           Tool call history
  ~/.claude/sessions/ summaries
```

**`/compact` vs. `/clear` — use the right one:**

```
/compact   Summarize and keep going.
           Use at phase transitions within the same task.
           Research done? /compact before planning.
           Plan confirmed? /compact before implementing.
           Debug resolved? /compact before continuing.

/clear     Full wipe. Fresh start.
           Use when switching to an unrelated task.
           NOT for switching phases of the same feature.
           YES for switching from one feature to a completely different one.
```

**Recovery pattern after a break:**

```
1. Open Claude Code in the project directory
2. Session-start hook fires automatically:
      Injects previous session summary
      If active ticket: injects ticket context
      Reports available session aliases
3. If more detail needed:
      /sessions list            browse all sessions
      /sessions load <id>       load a specific session
      /ticket GH-N              reload a specific ticket context
4. Continue: /tdd
```

**When to use `/checkpoint`:**

```
Use /checkpoint before:
  Clearing context (/clear) if you have local state worth keeping
  Risky git operations (rebase, force push, reset)
  Context reaches 50+ messages — safe rollback point
  End of a significant phase before opening a PR

/checkpoint create "phase-1-complete"
/checkpoint list
/checkpoint verify "phase-1-complete"   compare current vs snapshot
```

---

## Quality Standards

The agents and hooks enforce these mechanically, but you need to understand them to make good decisions — not just pass checks.

**The three comprehensibility checkpoints** (these appear twice in this guide — they are important enough to repeat):

```
Before merging any PR, answer all three:

1. Can I explain what this feature does and how it fits into the system?
2. Do I understand how the pieces connect: what calls what, how data flows?
3. If this breaks at 2am, do I know where to start investigating?

If any answer is "no" — do not merge.
```

**File and function size limits, and why they exist:**

```
800 lines max per file      Longer files have accumulated multiple
                            responsibilities. Split by domain.

50 lines max per function   If it does not fit on one screen, it is
                            doing too many things. Extract sub-functions.

4 levels max nesting        Deep nesting is control flow that has not
                            been extracted. Use early returns instead.
```

**Immutability — the concrete pattern:**

```
Never:  array.push(item)             // mutates the original
Always: [...array, item]             // creates a new array

Never:  obj.property = value         // mutates the original
Always: { ...obj, property: value }  // creates a new object

Why: mutable state produces bugs that are hard to trace because the
mutation can happen anywhere. Immutable patterns make every state
change explicit and visible.
```

**Atomic PRs — when a PR is too large:**

A PR is not atomic when any of these are true:
- 20+ files changed
- Description requires more than 1–2 bullet points
- Review is taking more than a day
- You feel nervous merging ("a lot could break")

Fix: split into sequenced issues, implement separately. Branches are cheap. Bundled PRs are expensive.

**When to abstract vs. when to wait:**

```
Abstract when you feel real pain:        Wait when you feel anticipated pain:

"I've written this same code 3 times"    "I might need this again someday"
"A bug fix requires changes in 5 places" "This could get complicated later"
"I cannot understand my own code"        "Someone might not understand this"
```

---

## Security: What to Check Before Every Commit

Security is not a phase — it is a continuous check at every commit. The `code-reviewer` flags CRITICAL security issues automatically, and `security-reviewer` provides deeper analysis for sensitive code.

**Pre-commit checklist:**

```
[ ] No hardcoded API keys, secrets, passwords, or tokens in code
    Why: committing a secret exposes it forever in git history.
    Use environment variables. If accidentally committed, rotate immediately.

[ ] All user inputs validated at system boundaries
    Why: validation on only the frontend is easily bypassed.
    Validate again on the server with schema validation (Zod, Pydantic, etc.)

[ ] SQL injection prevented — parameterized queries only
    Why: string concatenation in queries is not safe even with sanitization.
    Use parameterized queries or an ORM that handles this.

[ ] XSS prevented — sanitize user content before rendering
    Why: user content placed in innerHTML is a vulnerability.
    Use textContent, or DOMPurify for cases where HTML is required.

[ ] Authentication verified on all protected routes
    Why: test by accessing protected routes without a session.
    Authorization bugs are almost always found this way.

[ ] Rate limiting on public endpoints
    Why: without rate limiting, every public endpoint is a potential DoS vector.

[ ] Error messages do not leak internal details to clients
    Why: stack traces and internal paths reveal your architecture to attackers.
    Log details server-side; return generic messages to clients.

[ ] console.log does not log sensitive data
    Why: tokens, passwords, and PII in logs are a serious disclosure risk.
    The console.log scan hook catches this automatically.

[ ] Database access controlled at the database level
    Why: application-level checks alone are not sufficient.
    Use Row Level Security (RLS) or equivalent database-level access controls.
```

**Security response protocol:**

```
Security issue found?
  1. STOP immediately — do not continue implementing
  2. Invoke the security-reviewer agent
  3. Fix all CRITICAL issues before proceeding
  4. Rotate any exposed secrets (API keys, tokens, passwords)
  5. Scan the rest of the codebase for the same pattern
```

---

## Using with Gemini CLI

The system supports both Claude Code and Gemini CLI. The workflow is identical, with one key difference: Claude Code fires hooks automatically; Gemini CLI requires the session rituals to be run manually.

```
Claude Code:                  Gemini CLI:

  Hooks fire                    You run startup
  automatically                 ritual manually
       |                              |
  SessionStart hook       =    GEMINI.md §2 startup checklist
  (loads context)               (read active ticket, required files)
       |                              |
  Stop hook               =    GEMINI.md §3 shutdown checklist
  (saves session)               (run /handoff, commit changes)
```

**Startup checklist — run at the beginning of every Gemini session:**

```
[ ] Read .ai/tickets/active.md
[ ] If a ticket is set: read .ai/tickets/GH-{N}/context.md fully
[ ] Run /ticket status to confirm orientation
[ ] Read all files listed in "Files to Read Before Starting"
[ ] Identify the exact next action from "Handoff Instructions"
```

**Shutdown checklist — run before ending any Gemini session with in-progress work:**

```
[ ] Run /handoff
[ ] Confirm context.md shows Last Agent: gemini-cli
[ ] Commit all changes
```

**Agent availability:**

```
Claude Code:   9 agents in .claude/agents/
               (all agents including architect and database-reviewer)

Gemini CLI:    5 agents in .gemini/agents/
               (planner, tdd-guide, code-reviewer,
                security-reviewer, build-error-resolver)

Both platforms read from and write to the same .ai/tickets/ directory.
Handoffs between platforms work transparently.
```

**To edit agent instructions:** Edit `.ai/agents/{name}.md` (the source of truth), then run `node scripts/gen-agents.js` to regenerate both `.claude/agents/` and `.gemini/agents/`.

---

## Common Mistakes and How to Catch Them

If you see any of these signals, stop and address the underlying problem before continuing.

| Signal | What it means | What to do |
|--------|--------------|------------|
| "I cannot explain this code" | Shipping slop | Run `/code-review`. Ask for an architecture explanation. Do not merge. |
| 50+ messages in context | Context degradation | `/checkpoint` then `/clear`. Recover with session summary. |
| Claude referencing rejected ideas | Stale context | Externalize decisions to the issue, then reset context. |
| PR touches 20+ files | Scope creep | Split into atomic issues. Implement separately. |
| Tests written after implementation | TDD violation | Delete the implementation. Start with the test. |
| "This might break things" | Too much bundled | Ship smaller. Do not merge what you cannot debug. |
| Multiple features in one session | Context hygiene violation | One task, one context. Period. |
| Using `--no-verify` | Bypassing quality gates | Fix the underlying issue. Never bypass hooks. |
| Planning when still fuzzy | Premature commitment | Go back to Explore (Step 0). |
| Making claims about unread code | Hallucination risk | Read the file before making any claims about it. |

---

## Quick Reference

**What should I do right now?**

```
Idea is fuzzy?
  -> Explore: free-form chat, no commands, no code written

Idea is clear?
  -> /plan -> confirm -> issues auto-created in tracker -> new session -> /tdd GH-42

Continuing an existing feature in a new session?
  -> /tdd GH-42 (loads issue + context + creates branch in one command)

Implementation done?
  -> /verify -> /code-review -> fix CRITICAL/HIGH -> open PR

At a phase boundary (research done, plan confirmed, debug resolved)?
  -> /compact -> continue in same session with clean context

Switching to an unrelated task?
  -> /checkpoint -> /clear -> new session (auto-loads previous summary)

Something broke mid-implementation?
  -> Stay in context, debug, fix THEN clear

Build or type errors?
  -> /build-fix

Security issue found?
  -> STOP -> security-reviewer -> fix CRITICAL -> rotate secrets

Ending session with in-progress work?
  -> /handoff -> commit
```

**Command cheat sheet:**

```
/plan               Plan a feature; auto-creates issue in tracker + writes ticket context
/tdd GH-42          Load issue + context + create branch, then implement with TDD
/tdd ENG-42         Same, for Linear issues
/tdd                Continue active ticket (no arg = reads active.md)
/issue list         List issues in configured tracker (GitHub or Linear)
/issue create       Create an issue interactively in configured tracker
/issue view 42      View issue details (GH issue 42 or Linear ENG-42)
/issue close 42     Close an issue
/code-review        Review implementation before PR (80%+ confidence threshold)
/build-fix          Fix type/build errors with minimal diffs only
/e2e                Generate and run Playwright E2E tests
/refactor-clean     Remove dead code safely (one item at a time)
/verify             Full pre-PR check: build + types + lint + tests + coverage
/checkpoint         Named git snapshot + log entry
/ticket GH-N        Load ticket context, set as active
/ticket list        Show all tickets and their statuses
/handoff            Write current progress to ticket context before ending
/sessions           Browse and load previous session summaries
/learn              Extract reusable pattern from this session to skills
/skill-create       Generate SKILL.md from project git history
/update-skills      Regenerate skills/INDEX.md from disk
```

---

## CLI over MCP

The `/issue` command, `/plan`'s auto-create, and `/tdd`'s issue pull all use CLI tools directly (`gh`, `linear`) rather than MCP servers. This is intentional.

**Why CLI over MCP:**
- No MCP config or auth setup in Claude's settings — just authenticate the CLI once
- Doesn't consume context window (MCP tools load schemas that eat tokens)
- Easier to debug — you can run the same commands in your terminal to verify
- Works across Claude Code and Gemini CLI without platform-specific config

**The rule:** Use MCP only when a tool has no usable CLI. For GitHub, Linear, Supabase, Railway, and most developer tools — the CLI exists and is better.

---

## Further Reading

```
CLAUDE.md        Complete reference: all rules, templates, standards.
                 §8: Issue and PR templates.
                 §9: Security checklist.
                 §12: Anti-patterns and red flags.
                 §13: Hooks table.

GEMINI.md        Equivalent guide for Gemini CLI users.
                 Mandatory reading before using Gemini with this system.
                 §2: Startup ritual (mandatory).
                 §3: Shutdown ritual (mandatory).

.ai/agents/      Agent source files — edit here, then run gen-agents.js.
                 Do not edit .claude/agents/ or .gemini/agents/ directly.

skills/          Reference skill files for your stack.
                 See skills/INDEX.md for the full stack-organized index.
                 Only use skills declared in CLAUDE.md §4 (Tech Stack).
```
