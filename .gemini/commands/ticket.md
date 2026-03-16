# Ticket Command

Load a ticket context and orient yourself for implementation.

## Usage

```
/ticket GH-42       — load ticket, set as active
/ticket 42          — same (GH- prefix optional)
/ticket list        — list all ticket contexts
/ticket status      — show full active ticket
/ticket clear       — unset active ticket
```

## What to Do

### `/ticket GH-N`

1. Read `.ai/tickets/GH-{N}/context.md`
2. Write the ticket ID to `.ai/tickets/active.md`:
   ```
   # Active Ticket
   GH-{N}
   ## Last Set
   {datetime} by gemini-cli
   ```
3. Display a summary:
   - Title, Status, Last Phase
   - Next action from "Current State → In Progress"
   - Files listed under "Files to Read Before Starting"
4. Say: "Loaded GH-{N}: {title}. Status: {status}. Ready to continue from: {next action}."

### `/ticket list`

Scan `.ai/tickets/*/context.md` files and show a table with: ticket ID, status, title, last updated, last agent.

### `/ticket status`

Show the full content of the active ticket's `context.md`.

### `/ticket clear`

Write `(none)` to `.ai/tickets/active.md`.

## Notes

- Always run `/ticket GH-N` before `/tdd` on any new session
- Ticket contexts are written by the Claude `/plan` command or by `/handoff`
- See GEMINI.md §2 Startup Ritual for the full session startup checklist
