# Loop Start Command

Start a managed autonomous loop pattern with safety defaults.

## Usage

```
/loop-start [pattern] [--mode safe|fast]
```

- `pattern`: `sequential`, `continuous-pr`, `rfc-dag`, `infinite`
- `--mode safe` (default): strict quality gates and checkpoints
- `--mode fast`: reduced gates for speed

## What This Does

1. Confirms repository state and branch strategy
2. Selects loop pattern and model tier strategy
3. Activates required quality gates for the chosen mode
4. Creates a loop runbook under `.claude/plans/`
5. Prints commands to start and monitor the loop

## Safety Checks (Required Before First Iteration)

- Tests must pass before entering the loop
- Loop must have an explicit stop condition
- Quality gate profile must not be globally disabled

## Patterns

| Pattern | Use When |
|---------|----------|
| `sequential` | Known list of independent tasks, one at a time |
| `continuous-pr` | Keep opening PRs until the backlog is clear |
| `rfc-dag` | Large feature with a DAG of dependent units (see `ralphinho-rfc-pipeline` skill) |
| `infinite` | Monitoring or polling loop with a time-based stop |

## After Starting

Run `/loop-status` to check progress, phase, and any failing checks.

## Related Skill

See `./skills/continuous-agent-loop/SKILL.md` for loop pattern theory and risk mitigation.
