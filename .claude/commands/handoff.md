---
description: Write a cross-agent handoff to the active ticket context file before ending a session or switching agents.
---

# Handoff Command

Update the active ticket's context file with the current session's progress so any agent (Claude, Gemini, or future) can continue without losing context.

## Usage

```
/handoff              — update active ticket context
/handoff GH-42        — update specific ticket context
/handoff --status complete   — mark ticket as fully implemented
```

## When to Use

Run `/handoff` before:
- Ending a Claude Code session with uncommitted progress on a ticket
- Switching from Claude Code to Gemini CLI (or any other agent)
- Completing a phase and wanting to record clean state for the next session
- Handing off to another developer's AI setup

## What It Does

1. Determine the active ticket from `.ai/tickets/active.md` (or use the provided GH-N)
2. Read the current `.ai/tickets/GH-{N}/context.md`
3. Update the `Current State` section:
   - Check off completed steps (move to Completed with `[x]`)
   - Write precise In Progress status for any partial work
   - Set a concrete "Continue from" instruction in Handoff Instructions
4. Update `Implementation Notes` with decisions or discoveries from this session
5. Update metadata: `Last Updated`, `Last Agent: claude-code`, `Last Phase`
6. If `--status complete`: set Status to `implemented`
7. Write the updated file
8. Confirm: "Handoff written to `.ai/tickets/GH-{N}/context.md`. Next agent will continue from: {specific action}."

## Output Quality Standard

The "Continue from" line must be specific enough for an agent with no prior context to start immediately. Bad: "Continue implementation". Good: "Phase 2 Step 1: Create `src/components/PricingTable.tsx` — display three tiers with upgrade buttons."

## Notes

- This command writes prose — it cannot be done automatically by hooks
- Hooks update metadata (timestamps, last-agent) automatically at session end
- For the narrative Current State update, always run `/handoff` explicitly
