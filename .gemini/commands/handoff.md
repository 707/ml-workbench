# Handoff Command

Write a cross-agent handoff to the active ticket context file before ending a session.

## Usage

```
/handoff
/handoff GH-42
/handoff --status complete
```

## When to Run

**MANDATORY** — run before:
- Ending any Gemini session with uncommitted ticket progress
- Switching from Gemini CLI to Claude Code (or any other agent)
- Completing a phase and wanting clean state for the next session

This is the Gemini equivalent of the session-end hook. Since Gemini has no automatic hooks, you must run this explicitly.

## What It Does

1. Determine the active ticket from `.ai/tickets/active.md`
2. Read the current `.ai/tickets/GH-{N}/context.md`
3. Update `Current State`:
   - Check off completed steps with `[x]`
   - Write precise "In Progress" status for partial work
   - Set a specific "Continue from" line in Handoff Instructions
4. Append session decisions to `Implementation Notes`
5. Update metadata: `Last Updated`, `Last Agent: gemini-cli`, `Last Phase`
6. If `--status complete`: set Status to `implemented`
7. Write the updated file
8. Confirm: "Handoff written. Next agent continues from: {specific action}."

## Quality Standard for "Continue from"

Must be specific enough for a fresh agent with no prior context to start immediately.

Bad: "Continue implementation"
Good: "Phase 2 Step 3: Add `useSubscription` hook in `src/hooks/useSubscription.ts` — fetches subscription status from Supabase and returns tier"

## Notes

- This updates the prose Current State section — hooks cannot do this automatically
- The session-start hook (Claude) and GEMINI.md Startup Ritual both read this file
- See GEMINI.md §3 Shutdown Ritual for the full end-of-session checklist
