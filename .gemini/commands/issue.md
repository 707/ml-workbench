---
description: Manage issues in your configured issue tracker (GitHub or Linear).
---

# Issue Command

Create, list, view, and close issues in your configured issue tracker.

## Setup

Configure your tracker in `.claude/project.json` (gitignored — set once per machine):

```json
{
  "tracker": "github",
  "githubRepo": "owner/repo"
}
```

or for Linear:

```json
{
  "tracker": "linear",
  "linearTeam": "ENG",
  "linearProject": "Q1 2026"
}
```

**All fields:**

| Field | Required | Description |
|-------|----------|-------------|
| `tracker` | Yes | `"github"` \| `"linear"` \| `"none"` |
| `githubRepo` | No | `"owner/repo"` — omit to infer from `git remote origin` |
| `linearTeam` | If Linear | Team key, e.g. `"ENG"` |
| `linearProject` | No | Project name, e.g. `"Q1 2026"` — omit to create unassigned issues |

**First-time setup:**

```bash
# GitHub
gh auth login

# Linear
brew tap joa23/linear-cli https://github.com/joa23/linear-cli
brew install linear-cli
linear auth login
linear init   # creates .linear.yaml with team + project defaults
```

## Usage

```
/issue list
/issue create
/issue view <id>
/issue close <id>
```

## How It Works

Read `.claude/project.json` to determine tracker and config, then run the appropriate CLI:

### `/issue list`

```bash
# GitHub
gh issue list                            # infers repo from git remote
gh issue list --repo <githubRepo>        # if githubRepo is set

# Linear
linear issues list                       # all issues for team
linear issues list --project "<linearProject>"   # if linearProject is set
```

### `/issue create`

Prompt for title and description (or accept them inline), then:

```bash
# GitHub
gh issue create --title "<title>" --body "<body>"
gh issue create --repo <githubRepo> --title "<title>" --body "<body>"   # if githubRepo set

# Linear
linear issues create "<title>" --team <linearTeam> --description "<body>"
linear issues create "<title>" --team <linearTeam> --project "<linearProject>" --description "<body>"   # if linearProject set
```

After creation, output the issue URL and ID. The ID is ready to pass to `/plan` or `/tdd`.

### `/issue view <id>`

```bash
# GitHub (id = issue number, e.g. 42)
gh issue view <id> --json title,body,state,labels,assignees
gh issue view <id> --repo <githubRepo> --json title,body,state,labels,assignees   # if githubRepo set

# Linear (id = team-prefixed, e.g. ENG-42)
linear issues get <id> --format full
```

### `/issue close <id>`

```bash
# GitHub
gh issue close <id>
gh issue close <id> --repo <githubRepo>   # if githubRepo set

# Linear
linear issues update <id> --state Done
```

## Notes

- If `.claude/project.json` is missing or `tracker` is `"none"`, report: "No tracker configured. Add `.claude/project.json` with a tracker field."
- The issue ID returned by `/issue create` is what you pass to `/plan` and `/tdd`
- For GitHub, the issue number becomes `GH-{N}` in the `.ai/tickets/` directory
- For Linear, the issue ID (e.g., `ENG-42`) is used directly
