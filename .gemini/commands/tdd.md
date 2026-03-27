# TDD Command

Invoke the tdd-guide agent to implement a feature using test-driven development.

## Usage

```
/tdd
/tdd GH-42
```

## What This Does

### Step 0: Load Ticket Context (Before Anything Else)

**If an issue ID was passed** (e.g., `/tdd GH-42` or `/tdd ENG-42`):

1. Write issue ID to `.ai/tickets/active.md`
2. Read `.ai/tickets/{ISSUE-ID}/context.md` if it exists
3. Read `.claude/project.json` to determine tracker
4. Pull real issue body: `gh issue view {N} --json title,body,labels` or `linear issues get {ID} --format full`
5. If on `main`/`master`, create a feature branch: `git checkout -b feature/{issue-id}-{title-slug}`
6. Report: "Loaded {ISSUE-ID}: {title}. Branch: feature/{slug}. Starting from: {next action}."

**If no argument passed:**

1. Check `.ai/tickets/active.md` for the active ticket ID
2. If set: read context fully, orient from "Current State"
3. If no active ticket: ask "Which issue? Run `/tdd GH-42` or `/tdd ENG-42`."

### Steps 1-7: TDD Cycle

```
RED → GREEN → COMMIT → REFACTOR → REPEAT

RED:      Write a failing test first
GREEN:    Write minimal code to pass
COMMIT:   Commit after tests pass (before refactor)
REFACTOR: Improve code, keep tests passing
REPEAT:   Next step from the Confirmed Plan
```

**Commit format** (conventional commits):
```
feat: add notification bell component

Closes #42
```
Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
Issue reference: `Closes #N` (GitHub) or `ENG-42` (Linear)

For each step in the Confirmed Plan:
1. Write failing test (RED)
2. Run test — verify it fails
3. Write minimal implementation (GREEN)
4. Run test — verify it passes
5. Commit
6. Refactor if needed
7. Verify coverage ≥ 80%

## Important Rules

- **MANDATORY**: Write tests BEFORE implementation — never skip the RED phase
- **MANDATORY**: Mark each Confirmed Plan step as done/in-progress as you go
- **Before ending session**: run `/handoff` to update the ticket context

## Related Agent

This invokes the `tdd-guide` agent at `.gemini/agents/tdd-guide.md`.
