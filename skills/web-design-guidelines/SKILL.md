---
name: web-design-guidelines
description: UI/accessibility audit against Web Interface Guidelines. Use when reviewing UI code, checking accessibility, auditing design, or validating against web best practices.
origin: vercel-labs
---

# Web Interface Guidelines

Review files for compliance with Web Interface Guidelines — 100+ rules covering accessibility, animation, forms, and interaction patterns.

## When to Apply

Use this skill when asked to:
- "Review my UI code"
- "Check accessibility"
- "Audit design"
- "Review UX"
- "Check my site against best practices"

## How It Works

1. Fetch the latest guidelines from the source URL below
2. Read the specified files (or prompt user for files/pattern)
3. Check against all rules in the fetched guidelines
4. Output findings in the terse `file:line` format

## Guidelines Source

Fetch fresh guidelines before each review:

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

Use WebFetch to retrieve the latest rules. The fetched content contains all the rules and output format instructions.

## Usage

When a user provides a file or pattern argument:
1. Fetch guidelines from the source URL above
2. Read the specified files
3. Apply all rules from the fetched guidelines
4. Output findings using the format specified in the guidelines

If no files specified, ask the user which files or patterns to review.
