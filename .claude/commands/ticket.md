---
description: Set or view the active ticket context for cross-agent handoff. Loads .ai/tickets/GH-N/context.md and orients the current session.
---

# Ticket Command

Set the active ticket and load its context so any agent can orient itself toward a specific GitHub issue.

## Usage

```
/ticket GH-42       — load ticket context, set as active
/ticket 42          — same (GH- prefix optional)
/ticket list        — list all available ticket contexts
/ticket status      — show full active ticket context
/ticket clear       — unset active ticket
```

## What It Does

### `/ticket GH-N` — Load a Ticket

1. Read `.ai/tickets/GH-{N}/context.md`
2. Write `GH-{N}` to `.ai/tickets/active.md` with current timestamp
3. Display a summary:
   - Title and current status
   - Last agent and phase
   - Next action from "Current State"
   - Files to read before starting
4. Say: "Loaded GH-{N}. Ready to continue from: {next action}."

### `/ticket list` — List All Tickets

Scan `.ai/tickets/*/context.md` and display a table:

```
GH-42  | planning-complete | Add Stripe billing        | 2026-02-26 | claude-code
GH-43  | in-progress       | User dashboard redesign   | 2026-02-25 | gemini-cli
GH-44  | implemented       | Fix login redirect loop   | 2026-02-24 | claude-code
```

### `/ticket status` — Show Active Ticket

Display the full content of `.ai/tickets/active.md` and the corresponding `context.md`.

### `/ticket clear` — Unset Active Ticket

Write `(none)` to `.ai/tickets/active.md` and confirm.

## When to Use

- At the start of any implementation session: `/ticket GH-42` before `/tdd`
- After switching from another agent (Gemini → Claude): run `/ticket status` to confirm orientation
- After a context reset: reload the ticket so the new session has full context

## Notes

- Ticket context files live at `.ai/tickets/GH-{N}/context.md`
- The active ticket is automatically loaded by the session-start hook
- Use `/handoff` to write a cross-agent handoff before ending a session
