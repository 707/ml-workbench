# Ticket Context Files

This directory contains cross-agent handoff documents for active GitHub issues.

## What These Files Are

Each ticket gets a `GH-{N}/context.md` file that captures:
- The confirmed implementation plan (written by `/plan`)
- Which files to read before starting
- Current implementation state (what's done, what's in progress)
- Handoff instructions for the next agent or session

## Why They Exist

These files enable seamless handoffs between AI agents and across sessions:
- Plan in Claude Code → implement in Gemini CLI (or vice versa)
- Resume work after a context reset without losing the plan
- Any agent can orient itself by reading one file

## Lifecycle

1. **Created** — by `/plan` after user confirms the implementation plan
2. **Updated** — by `/handoff` before ending any session with uncommitted work
3. **Auto-loaded** — by session-start hooks (Claude) and GEMINI.md startup ritual (Gemini)
4. **Archived** — when ticket status is set to `reviewed` (keep for reference)

## Active Ticket

`active.md` in this directory is a runtime pointer to the current ticket.
It is gitignored — each developer sets their own active ticket locally.

## Format

See any `GH-{N}/context.md` for the canonical format. The key sections are:
- Status / Last Agent / Last Phase (metadata)
- Confirmed Plan (authoritative — do not re-plan)
- Files to Read Before Starting
- Current State (completed / in-progress / blocked)
- Handoff Instructions (where to continue from)
