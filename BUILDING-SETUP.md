# BUILDING.md — Self-Installing Build Journal

> **You are reading a setup file.** When Claude Code reads this file, it will explore your project, learn what it can on its own, then ask you a couple of high-level questions to fill in the gaps. After setup, this file replaces itself with your customized BUILDING.md. Zero friction.

---

## How to Use

1. Place this file in your project root
2. Open Claude Code in your project directory
3. Say: **"Read BUILDING-SETUP.md and follow the instructions"**
4. Give it permission to explore, answer 2-3 questions
5. Done. Your personalized BUILDING.md is ready.

---

## Instructions for Claude

**IMPORTANT: When you read this file, you are the setup wizard. Follow these steps exactly. Do not summarize this file to the user. Do not read back these instructions. Just run them — starting with Step 1.**

### Step 1: Introduction

This is the first thing the user sees. Make it feel personal — like Eddie is talking to them through the wizard. Say something like this (adapt naturally, don't read it robotically):

> "Hey — this is BUILDING.md, a self-installing build journal created by Eddie Belaval ([@eddiebe](https://x.com/eddiebe)).
>
> Here's the idea: every project has a story, but most of that story lives in your head and disappears when the session ends. BUILDING.md captures it automatically — so when you look back in six months, you don't just see code, you see the journey.
>
> Here's what you're getting:"

Then explain the features — present them clearly, with a bit of energy:

> **Auto-updating build log** — After every significant piece of work (new feature, architecture decision, major fix), the journal updates itself. You don't have to remember to write anything down. It just grows as you build.
>
> **Periodic check-ins** — Every few milestones, I'll pause and ask you three quick questions: How's it going? What's next? What have you learned? These check-ins capture the human side — your mood, your direction, your reflections. They're the entries you'll value most later.
>
> **Origin story interview** — After setup, we'll do a quick conversational interview about how this project started. The spark, the problem, the early days. This becomes the opening chapter of your build journal.
>
> **Smart setup** — I'll explore your project first (package.json, git history, file structure, deployment config) and figure out as much as I can on my own. Then I'll only ask you the stuff I can't figure out — your philosophy, what you want to track, the high-level stuff.
>
> **Self-cleaning** — This setup file deletes itself when we're done. All that's left is your BUILDING.md, personalized to your project, ready to grow.

Then pause and ask:

> "That's the full picture. Before we start the setup — any questions? Anything you'd want to add, change, or configure differently?"

**Wait for their response.** If they have questions, answer them honestly. If they want to change something (like "I don't want check-ins" or "I want weekly check-ins instead of every 5 entries"), note it and adjust the setup accordingly. If they say something like "sounds good, let's go" or "no questions," proceed to Step 2.

### Step 2: Permission to Explore

Say something like:

> "Cool. Let me look around your codebase first so I don't waste your time with questions I can answer myself. I'll come back with what I found."

Then ask using AskUserQuestion:
- "Go for it — explore my project" (Recommended)
- "I'd rather just answer questions manually"

If they choose manual, skip to Step 6 (Fallback Interview). Otherwise, proceed to Step 3.

### Step 3: Autonomous Exploration

**Run all of these in parallel where possible. Be fast. The user is waiting.**

#### 2a: Project Identity
- Read `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, `pubspec.yaml`, `Gemfile`, or whatever manifest exists
- Extract: project name, version, description, dependencies, scripts
- Read `README.md` if it exists — extract the project description and any stated purpose
- Check the directory name as fallback for project name

#### 2b: Tech Stack Detection
From the manifest and file structure, determine:
- **Language:** TypeScript, Python, Rust, Go, Ruby, Swift, etc.
- **Framework:** Next.js, React, Vue, Django, FastAPI, Rails, etc. (check dependencies)
- **Database:** Look for Supabase, Prisma, Drizzle, SQLAlchemy, migrations folders, `.env` references
- **Deployment:** Check for `vercel.json`, `netlify.toml`, `Dockerfile`, `fly.toml`, `.github/workflows/`, `railway.json`, `render.yaml`
- **Testing:** Check for `jest.config`, `vitest.config`, `pytest.ini`, `__tests__/`, `tests/`, `spec/`

#### 2c: Project Shape
- Run `ls` on the root directory to understand the top-level structure
- Use Glob to check for common patterns: `src/`, `app/`, `lib/`, `components/`, `api/`, `docs/`
- Estimate project maturity: Is this a fresh scaffold or an established codebase? (check file count, git history depth)

#### 2d: Git Intelligence
- Check if this is a git repo (`git log --oneline -20` for recent history)
- Count contributors from `git shortlog -sn --all` — infer solo vs team
- Look at branch patterns (`git branch -a`) — infer branching strategy
- Check commit message style — are they conventional commits? Freeform? Stage-prefixed?
- Find the first commit date — how old is this project?

#### 2e: Existing Documentation
- Check for existing `BUILDING.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `ADR/`, `docs/`
- Check for `CLAUDE.md` or `.claude/` — are they already using Claude Code conventions?
- Check for `PIPELINE_STATUS.md` or any methodology markers

#### 2f: Project Type Classification
Based on everything found, classify:
- Web app, mobile app, CLI, library, API, monorepo, or hybrid
- Greenfield vs. established
- Solo vs. team
- Has CI/CD vs. manual deployment

### Step 4: Present Findings and Ask What Matters

After exploration, present a brief summary to the user. Something like:

> "Here's what I found:"
> - **Project:** [name] — [description or best guess]
> - **Stack:** [language + framework + database + deployment]
> - **Team:** [solo/team based on git contributors]
> - **Maturity:** [new project / active development / established codebase]
> - **Existing docs:** [what exists already]
>
> "Let me know if any of that's off. Now the stuff only you can tell me:"

Then ask these — **the only questions the user needs to answer:**

**Question 1 — What should this document track?**
Ask using AskUserQuestion (multiSelect: true):
- Architecture decisions and rationale
- Chronological build log (what was built when)
- Design/UX decisions
- Key learnings and pivots
- Sprint/milestone tracking
- Testing and quality strategy

**Question 2 — Your building philosophy**
Ask conversationally: "In a sentence or two — what's your building philosophy? What matters to you when you ship?"

Give examples if they seem stuck: "Some people say 'ship fast, iterate faster.' Others say 'test everything before it goes live.' Others say 'user experience above all else.' What's yours?"

**Question 3 — Depth gate**
Ask using AskUserQuestion:
- "That's enough — generate my BUILDING.md" (Recommended)
- "Let's go deeper — I want to customize more"

### Step 5: Deep Customization (Only If They Chose "Go Deeper")

Only ask questions the exploration couldn't answer:

- **Documentation style preference:** Narrative (prose), Structured (tables/checklists), or Hybrid?
- **Audience:** Just me, my team, public/open-source, or judges/evaluators?
- **Anything unique:** "Is there anything specific about your project or workflow that BUILDING.md should capture?"

If the exploration already detected a methodology (from commit patterns, existing docs, etc.), confirm it rather than asking from scratch: "It looks like you're using [X] — should I structure the journal around that?"

### Step 6: Fallback Interview (Only If They Declined Exploration)

If the user chose "I'd rather just answer questions manually" in Step 1, run this minimal interview:

1. **Project name and one-liner** (conversational)
2. **Tech stack** (conversational)
3. **Solo or team?** (AskUserQuestion: Solo / Small team / Larger team)
4. **What should this track?** (AskUserQuestion, multiSelect — same as Question 1 above)
5. **Building philosophy** (conversational — same as Question 2 above)

Then proceed to Step 7.

### Step 7: Generate BUILDING.md

Based on everything — exploration results + user answers — generate a complete BUILDING.md. Follow these rules:

**Structure Rules:**
1. Start with `# Building [Project Name]` as the title
2. Include a 2-3 sentence overview using real project details (not placeholders)
3. Include a Table of Contents with anchor links
4. Include a "Stack" section with the detected/confirmed tech stack
5. Organize remaining sections based on what they selected in "what should this track"
6. For each section, provide:
   - A brief description of what goes in this section
   - A starter entry pre-filled with real data from the exploration (git history, current state, etc.)
   - Clear formatting so they (or Claude) can add entries naturally
7. End with a "How to Use This Document" section:
   - Explain that BUILDING.md updates itself — Claude will auto-update it after significant work
   - Mention they can also manually request updates anytime ("update BUILDING.md with [what happened]")
   - The philosophy: living document, not a chore
8. **CRITICAL — Add the auto-update protocol as the very last thing in the file.** This is what makes the journal self-maintaining. Append this HTML comment block at the bottom of every generated BUILDING.md:

```
<!-- BUILDING.md Auto-Update Protocol

Claude: This is a living build journal. When you are working in this project, you MUST update this document automatically. Do not ask. Do not announce. Just do it as a natural side effect of building.

=== AUTO-UPDATE TRIGGERS ===

ALWAYS UPDATE FOR:
- New feature shipped → Add to Build Log with what was built and WHY
- Architecture decision made → Add to Architecture Decisions with context, alternatives considered, and rationale
- Significant bug fixed → Add to Build Log with what broke, root cause, and the fix
- Milestone reached → Add to Build Log with milestone summary
- Important lesson learned → Add to Lessons Learned
- Sprint/phase completed → Update Sprint/Milestone Tracking
- Major refactor → Add to Build Log with what changed and why
- Dependency or stack change → Update Stack section + add Build Log entry

NEVER UPDATE FOR:
- Typo fixes, formatting changes, comment edits
- Minor dependency bumps with no behavior change
- Routine test additions (unless establishing a new testing strategy)
- File renames or moves with no architectural significance

HOW TO UPDATE:
1. Read the current BUILDING.md first
2. Add new entries to the appropriate section (don't rewrite existing content)
3. Match the existing voice and style (first person for solo, "we" for teams)
4. Include the date on each entry
5. Focus on the WHY, not just the what — decisions and reasoning are more valuable than descriptions
6. Keep entries concise but complete — 2-5 sentences per entry is typical

=== CHECK-IN SYSTEM ===

After every 5th auto-update entry (count the entries you've added during this session and across recent sessions), trigger a CHECK-IN. A check-in is a brief conversational interview with the builder. It captures the human side of the build at regular intervals — mood, direction, reflection.

WHEN TO TRIGGER:
- After the 5th auto-update entry since the last check-in (or since the origin story if no check-ins yet)
- After completing a major milestone (version bump, launch, significant pivot)
- After a long gap (if the last BUILDING.md entry is more than 2 weeks old and work is resuming)

HOW TO RUN A CHECK-IN:
1. Pause naturally after completing the work that triggered the check-in
2. Say something like: "Your build journal has grown a lot since the last check-in. Quick pulse check — three questions, takes a minute."
3. Ask these conversationally, one at a time:
   - "How's the build going? How are you feeling about where things stand?"
   - "What's your next target? What are you aiming for next?"
   - "Anything you've learned or realized since we last checked in that's worth capturing?"
4. Write a "## Check-in — [Date]" section in BUILDING.md with their answers
5. Keep it in their voice — casual, honest, real. Not polished. These are the entries they'll value most when they look back.
6. If they wave it off ("skip" / "not now" / "later"), respect it and reset the counter. Try again after the next 5 entries.

CHECK-IN FORMAT:
## Check-in — YYYY-MM-DD

**Mood:** [their words about how it's going]
**Next target:** [what they're aiming for]
**Reflection:** [anything they've learned or realized]

---

The check-ins are what make this a biography, not a changelog. The auto-updates capture what happened. The check-ins capture who was building it and how they felt along the way.

=== PROTOCOL RULES ===

This protocol is invisible to the user. The journal grows organically as a side effect of building. Auto-updates happen silently. Check-ins happen conversationally at natural pause points. The goal: when the builder reads this document in six months, they don't just see what they built — they see who they were while building it.
-->
```

**This comment block is non-negotiable. Every generated BUILDING.md must include it. It is the mechanism that makes the journal self-maintaining.**

**Content Rules:**
- Use REAL data from the exploration — actual dependency names, actual commit counts, actual project structure
- Use the user's own words for philosophy and priorities
- If they have git history, include a "Current State" entry that summarizes where the project stands right now
- If this is a new project, include a "Day 1" entry that captures the starting point
- If they chose "narrative" style, write in prose
- If they chose "structured" style, use tables and bullets
- If they chose "hybrid" or didn't specify, use hybrid (narrative intros + structured details)
- If they selected "Architecture decisions," include an ADR section with a template
- If they selected "Build log," include a chronological log with a real first entry
- If they selected "Key learnings," include a "Lessons Learned" section
- If they selected "Sprint tracking," include a sprint/milestone tracker
- If they selected "Testing strategy," include a quality section noting what testing exists

**Tone Rules:**
- Solo builders get first person ("I built...", "I decided...")
- Teams get collaborative voice ("We built...", "The team decided...")
- Public/judges audience gets slightly more polished prose
- Personal audience gets casual, direct voice

**If a methodology was detected or stated, include:**
- A brief explanation of their methodology
- Structure that matches their approach (stages, sprints, kanban columns, etc.)
- Checkpoint prompts appropriate to their method

### Step 8: Write and Clean Up

1. Write the generated content to `./BUILDING.md` using the Write tool
2. Delete this setup file (`./BUILDING-SETUP.md`) using Bash: `rm ./BUILDING-SETUP.md`
3. Say something like:

> "Your BUILDING.md is set up and the setup file is gone. One more thing before we start building —"

Then immediately proceed to Step 9. **Do not wait for a response.** The origin interview is part of the setup flow, not a separate task.

**Do not ask for permission to delete the setup file. The self-cleanup is part of the design. Just do it.**

### Step 9: Origin Story Interview

This is the most important step. Every biography starts before the first chapter. The origin story is how the project got its soul on paper.

**Transition naturally — don't make it feel like a separate phase.** Say something like:

> "Every project has a story before the first commit. Let's get yours down while it's fresh. This becomes the opening entry in your build journal — the 'how it all started' that you'll look back on in six months and be glad you captured."

Then ask using AskUserQuestion:
- "Let's do it — ask me about the origin" (Recommended)
- "Skip for now — I'll add it later"

**If they skip, end the wizard here** with: "All set. Your BUILDING.md is ready. When you hit a milestone or make a key decision, just tell me to update it."

**If they want the interview, run it conversationally.** This is NOT a form. This is a conversation. Ask one question at a time, respond to what they say, ask follow-ups that feel natural. The goal is to pull out their story, not fill in a template.

**The origin questions (ask naturally, not as a numbered list):**

1. **The spark:** "What made you start this project? Was there a specific moment, conversation, or frustration that kicked it off?"

2. **The problem:** "What problem were you trying to solve — and who were you solving it for?"

3. **The early days:** "What did the first version look like? Was there a prototype, a sketch, a late-night hack? Or did you start with a plan?"

4. **The pivot (if applicable):** "Has the project changed direction since you started? What did you learn that shifted things?"

5. **The vision:** "Where do you want this to go? Not the roadmap — the feeling. What does success look like for this project?"

**You don't have to ask all five.** Read the room. If their answer to the spark question tells you the problem and the early days, skip ahead. If they're short on words, probe gently. If they're pouring out a story, let them talk and capture everything.

**After the interview, write the origin story:**

1. Read the current `./BUILDING.md`
2. Add an "## Origin" or "## How It Started" section — place it right after the overview/intro, before the technical sections
3. Write the origin story in their voice (first person for solo, "we" for teams)
4. Use their actual words and phrasing — not a polished rewrite, but a cleaned-up version of what they said
5. Keep it 3-6 paragraphs. Long enough to capture the arc, short enough that it doesn't feel like a chore to read
6. Use the Edit tool to add it to the existing BUILDING.md — do NOT rewrite the whole file

**After writing the origin story, confirm:**

> "Your origin story is in BUILDING.md. That's the arc — from how it started to where it's going. Everything you build from here gets added to the journal. When you ship something, make a key decision, or learn something worth remembering — just tell me to update BUILDING.md."

**That's the end of the wizard. The setup file is gone, the journal is alive, and it starts with a real story.**

---

## Credits

Built by **Eddie Belaval** — founder of id8Labs, filmmaker turned builder, shipping AI-augmented products out of Miami.

This started as a methodology I developed during a hackathon sprint where I wrote 3,600 lines of build documentation alongside the code itself. Turns out, documenting what you're building *while you're building it* changes how you think about the work. The journal becomes part of the architecture. The decisions you capture become the foundation for the next ones.

I wanted to share that with you. Not as a template you have to fill in — as a system that sets itself up and gets out of your way.

If this helped you, or if you built something cool with it, I'd love to hear about it. Engineer to engineer — we're all figuring this out together.

**X:** [@eddiebe](https://x.com/eddiebe)
**GitHub:** [eddiebelaval](https://github.com/eddiebelaval)
**id8Labs:** [id8labs.app](https://id8labs.app)

---

*This message will self-destruct in 5... 4... 3...*

*Good luck on your mission. Should you or any member of your team be caught scrolling to the bottom of a setup file instead of building, the Secretary will disavow any knowledge of your actions.*

*But seriously — if you read this far, you're my kind of person. Now go build something.*
