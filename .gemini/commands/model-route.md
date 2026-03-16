# Model Route Command

Recommend the best model tier for the current task by complexity and budget.

## Usage

```
/model-route [task-description] [--budget low|med|high]
```

## Routing Heuristic

| Tier | Use When |
|------|----------|
| `flash` / fast | Deterministic, low-risk mechanical changes |
| `gemini-2.5-pro` | Default for implementation, refactors, and review |
| `gemini-2.5-pro` (deep-think) | Architecture decisions, deep review, ambiguous requirements |

## Required Output

- recommended model tier
- confidence level (high / medium / low)
- why this tier fits the task
- fallback tier if first attempt is insufficient

## When to Use

Use this before starting a large or ambiguous task to calibrate model spend. Especially useful when operating under a token budget or cost constraint (`--budget low`).
