# Quality Gate Command

Run the quality pipeline on demand for a file or project scope.

## Usage

```
/quality-gate [path|.] [--fix] [--strict]
```

- default target: current directory (`.`)
- `--fix`: allow auto-format/fix where configured
- `--strict`: fail on warnings

## What This Does

1. Detects language and tooling for the target path
2. Runs formatter checks (Biome, Prettier, or similar)
3. Runs lint and type checks when available
4. Produces a concise remediation list with file paths and line numbers

Use `--fix` to auto-correct formatting issues. Use `--strict` to treat warnings as failures before a PR.

## When to Use

- Before opening a PR when you want a single-pass quality check
- After a large refactor to catch format drift
- Instead of relying on the PostToolUse hooks when working outside normal edit flow

## Related

Mirrors the PostToolUse hook behavior from `.claude/settings.json` but is operator-invoked on any path.
