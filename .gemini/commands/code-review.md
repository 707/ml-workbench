# Code Review Command

Invoke the code-reviewer agent to review code for quality, security, and maintainability.

## Usage

```
/code-review
```

## What This Does

The code-reviewer agent will:

1. Run `git diff --staged` and `git diff` to see all changes
2. Review each changed file using the full review checklist (CRITICAL → LOW)
3. Report findings by severity with specific file paths and line numbers
4. Give a final verdict: Approve / Warning / Block

## Severity Levels

- **CRITICAL**: Hardcoded secrets, SQL injection, XSS, auth bypasses — must fix before merge
- **HIGH**: Large functions, missing error handling, mutation patterns, missing tests
- **MEDIUM**: Performance issues, unnecessary re-renders
- **LOW**: TODOs without tickets, poor naming, magic numbers

## Verdict

- **Approve**: No CRITICAL or HIGH issues
- **Warning**: HIGH issues only (can merge with caution)
- **Block**: CRITICAL issues — fix before merge

## After Review

1. Fix all CRITICAL and HIGH issues
2. Open a PR with the PR Description Template from GEMINI.md §9
3. Verify security checklist (GEMINI.md §10) before marking ready

## Related Agent

This invokes the `code-reviewer` agent at `.gemini/agents/code-reviewer.md`.
