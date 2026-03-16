# Update Skills Index

Regenerate `skills/INDEX.md` from all skill folders currently on disk.

## When to Use

After manually adding, removing, or renaming any folder inside `skills/`.

## Instructions

1. Run: `node scripts/update-skills-index.js`
2. Read the output and report back:
   - Total skill count and per-stack breakdown
   - Any skills that ended up in "Uncategorized" — these have neither a built-in
     stack mapping nor a `stack:` field in their SKILL.md frontmatter
   - The path of the updated INDEX.md

3. If any uncategorized skills are found, show the user which ones they are and
   explain how to fix them: add `stack: <value>` to the SKILL.md frontmatter,
   then run `/update-skills` again.

   Valid stack values: `web`, `python`, `go`, `java`, `swift`, `cpp`, `database`, `general`

## Output Format

```
INDEX.md updated — <N> skills across <N> stacks

  Web / TypeScript / JavaScript      14 skills
  Python                              6 skills
  ...

  ⚠  2 uncategorized skills (add `stack:` frontmatter to fix):
     - my-new-skill
     - another-skill
```
