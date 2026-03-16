# Plan Command

Invoke the planner agent to create a comprehensive, phased implementation plan before writing any code.

## Usage

```
/plan I need to add [feature description]
/plan GH-42
```

## What This Does

1. Invokes the `planner` agent
2. The planner will:
   - Restate requirements clearly
   - Break the feature into phases with specific steps and file paths
   - Identify dependencies, risks, and testing strategy
   - **Wait for your explicit confirmation** before touching any code
3. After you confirm: the planner reads `.claude/project.json`, creates the issue via `gh issue create` (GitHub) or `linear issues create` (Linear), then writes `.ai/tickets/{ISSUE-ID}/context.md` and sets `active.md`

## Important

**CRITICAL**: The planner will NOT write any code until you explicitly confirm the plan.

If you want changes, respond with:
- "modify: [your changes]"
- "different approach: [alternative]"
- "skip phase 2 and go straight to phase 3"

## After Planning

Once the ticket context is written:
1. Close this Gemini session if you want implementation in a fresh context
2. Run `/tdd {ISSUE-ID}` to load the issue and begin test-driven implementation in one step

## Related Agent

This invokes the `planner` agent at `.gemini/agents/planner.md`.
