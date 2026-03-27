# Harness Audit Command

Audit the project-template agent harness setup and return a prioritized scorecard.

## Usage

`/harness-audit [scope] [--format text|json]`

- `scope` (optional): `repo` (default), `hooks`, `skills`, `commands`, `agents`
- `--format`: output style (`text` default, `json` for automation)

## What to Evaluate

Score each category from `0` to `10`:

1. Tool Coverage
2. Context Efficiency
3. Quality Gates
4. Memory Persistence
5. Eval Coverage
6. Security Guardrails
7. Cost Efficiency

## Output Contract

Return:

1. `overall_score` out of 70
2. Category scores and concrete findings
3. Top 3 actions with exact file paths
4. Suggested ECC skills to apply next

## Checklist

### Agents (10 expected)
Verify all 10 canonical agents exist in `.ai/agents/` and are synced to `.claude/agents/` and `.gemini/agents/` via `scripts/gen-agents.js`:
- `architect.md`
- `build-error-resolver.md`
- `code-reviewer.md`
- `database-reviewer.md`
- `e2e-runner.md`
- `harness-optimizer.md`
- `planner.md`
- `refactor-cleaner.md`
- `security-reviewer.md`
- `tdd-guide.md`

Check that `.ai/agents/` source files match `.claude/agents/` generated files (no drift). Verify `scripts/agent-config.json` has entries for all agents.

### Commands
Inspect `.claude/commands/` for the expected command set. Flag any commands referenced in CLAUDE.md that are missing from `.claude/commands/`.

### Hooks
Inspect `.claude/settings.json` for the 6 hook categories:
- `PreToolUse`: git push reminder, doc file warning, compact suggestion
- `PostToolUse`: PR logger, auto-format JS/TS, TypeScript type check, console.log warning, skills INDEX regeneration
- `Stop`: session summary persistence, console.log scan
- `SessionStart`: auto-load session summary
- `PreCompact`: log compaction event

Flag missing or broken hook commands. Verify hook scripts exist in `scripts/`.

### Skills
Inspect `skills/` directory. Verify `skills/INDEX.md` is up-to-date (run `node scripts/update-skills-index.js --dry-run` to check for drift). Flag skills present in `skills/` but missing from INDEX.md.

### Agent-Config Sync
Verify `scripts/agent-config.json` entries match files in `.ai/agents/`. Flag agents in config with no corresponding source file, or source files with no config entry.

### Stale References
Flag broken or stale references in CLAUDE.md, GEMINI.md, or command files pointing to non-existent agents/skills/commands.

## Example Result

```text
Harness Audit (repo): 58/70
- Tool Coverage: 9/10
- Context Efficiency: 8/10
- Quality Gates: 9/10
- Memory Persistence: 7/10
- Eval Coverage: 6/10
- Security Guardrails: 10/10
- Cost Efficiency: 9/10

Agent Sync: ✓ All 10 agents present in .ai/agents/ and .claude/agents/
Agent-Config Sync: ✓ agent-config.json matches source files
Skills INDEX: ⚠ 2 skills missing from INDEX.md (run update-skills-index.js)
Hooks: ✓ All 6 hook categories present

Top 3 Actions:
1) Run node scripts/update-skills-index.js to fix INDEX.md drift
2) Add eval coverage for tdd-guide agent in skills/eval-harness/
3) Add cost tracking to PostToolUse hooks in .claude/settings.json
```

## Arguments

$ARGUMENTS:
- `repo|hooks|skills|commands|agents` (optional scope)
- `--format text|json` (optional output format)
