# Project Template

A structured agent development scaffold.

## What is this?

Specialist agents, slash commands, automatic quality hooks, and a ticket context system to keep implementation focused and sessions resumable. Copy it into any new project and start Claude Code.

---

### Setup

1. Copy this folder into your project
2. (Optional) Open `CLAUDE.md` or `GEMINI.md` and fill in the PROJECT SETUP block at the top project name, tech stack, issue tracker URL
3. (Optional) Ask Claude or Gemini: `"Read BUILDING-SETUP.md and follow the instructions"` — sets up your build journal and then deletes itself
4. Start working — hooks, agents, and commands are already active

> ⚠️ Gemini still needs command and hooks implementation - WIP



### The loop

```
Explore → Plan → Issues → Implement → Review
```

- **Explore** — Free-form thinking in chat. No code, no commands. Clarify the problem.
- **Plan** — Run `/plan`. The planner agent produces a phased plan. Confirm it before moving on.
- **Issues** — Break the plan into atomic, sequenced issues in your tracker (GitHub, Linear, etc.).
- **Implement** — Open a fresh session. Run `/tdd ISSUE-ID`. The agent reads the ticket context, creates a branch, and works test-first.
- **Review** — Run `/code-review` when done. Fix findings. Open PR.

Run `/handoff` at the end of any session to save state. The next session picks up exactly where you left off. `/checkpoint` for a git commit save state.

### (Optional) Agent generation

Agents are defined once in `.ai/agents/`. Run `node scripts/gen-agents.js` to regenerate both `.claude/agents/` and `.gemini/agents/` from that single source. Edit agent instructions in `.ai/agents/` only.

### Contents

| Path | Purpose |
|------|---------|
| `CLAUDE.md` | Authoritative workflow guide for Claude Code |
| `GEMINI.md` | Authoritative workflow guide for Gemini CLI |
| `BUILDING-SETUP.md` | Self-installing wizard that generates your build journal |
| `USER-GUIDE.md` | Explains every component and why it exists |
| `.claude/agents/` | 10 specialist agents (planner, tdd-guide, code-reviewer, architect, security-reviewer, and more) |
| `.claude/commands/` | 15+ slash commands (`/plan`, `/tdd`, `/code-review`, `/handoff`, etc.) |
| `.claude/settings.json` | 10 automatic hooks (format, typecheck, console.log warnings, session save/load) |
| `.ai/agents/` | Platform-agnostic agent source — edit here, regenerate for Claude and Gemini |
| `.ai/tickets/` | Per-issue context files that preserve confirmed plans across sessions |
| `scripts/` | `gen-agents.js` (regenerate agents), hook implementations |
| `skills/` | 65+ reference files organized by tech stack (opt-in by declaring stack in setup) |