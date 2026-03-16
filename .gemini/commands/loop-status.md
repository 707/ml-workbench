# Loop Status Command

Inspect active loop state, progress, and failure signals.

## Usage

```
/loop-status [--watch]
```

## What This Reports

- active loop pattern
- current phase and last successful checkpoint
- failing checks (if any)
- estimated time and cost drift vs. plan
- recommended intervention: `continue` / `pause` / `stop`

## Watch Mode

`--watch` refreshes status periodically and surfaces state changes as they occur. Use this when monitoring a long-running loop.

## Interventions

| Signal | Recommended Action |
|--------|-------------------|
| Failing quality checks | Pause loop, fix root cause, resume |
| Cost drift > 2× estimate | Review scope, consider stopping |
| Same checkpoint repeated | Loop is stuck — stop and investigate |
| No checkpoint in > 30 min | Check for runaway or blocked tool call |

## Related

- `/loop-start` — start a loop
- `./skills/continuous-agent-loop/SKILL.md` — loop patterns and risk mitigation
