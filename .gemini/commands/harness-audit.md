# Harness Audit Command

Audit the project-template agent harness setup and return a prioritized scorecard.

## Usage

```
/harness-audit [scope] [--format text|json]
```

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

## Output

Returns:

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

Check that `.ai/agents/` source files match generated files (no drift). Verify `scripts/agent-config.json` has entries for all agents.

### Commands
Inspect `.claude/commands/` and `.gemini/commands/` for expected command sets. Flag commands present in one platform but missing from the other.

### Hooks
Inspect `.claude/settings.json` for the 6 hook categories:
- `PreToolUse`: git push reminder, doc file warning, compact suggestion
- `PostToolUse`: PR logger, auto-format JS/TS, TypeScript type check, console.log warning, skills INDEX regeneration
- `Stop`: session summary persistence, console.log scan
- `SessionStart`: auto-load session summary
- `PreCompact`: log compaction event

Flag missing or broken hook commands.

### Skills
Inspect `skills/` directory. Verify `skills/INDEX.md` is up-to-date. Run `node scripts/update-skills-index.js` to check for drift.

### Agent-Config Sync
Verify `scripts/agent-config.json` entries match files in `.ai/agents/`.

## Example Result

```text
Harness Audit (repo): 58/70
- Tool Coverage: 9/10
- Quality Gates: 9/10
- Eval Coverage: 6/10
- Cost Efficiency: 9/10

Agent Sync: ✓ All 10 agents present
Skills INDEX: ⚠ 2 skills missing from INDEX.md

Top 3 Actions:
1) Run node scripts/update-skills-index.js to fix INDEX.md drift
2) Add eval coverage for tdd-guide agent in skills/eval-harness/
3) Add cost tracking to PostToolUse hooks in .claude/settings.json
```

## Related Agent

This can be invoked by the `harness-optimizer` agent at `.gemini/agents/harness-optimizer.md`, which will apply the top recommendations automatically.
