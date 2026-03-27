---
description: Restate requirements, assess risks, and create step-by-step implementation plan. WAIT for user CONFIRM before touching any code.
---

# Plan Command

This command invokes the **planner** agent to create a comprehensive implementation plan before writing any code.

## What This Command Does

1. **Restate Requirements** - Clarify what needs to be built
2. **Identify Risks** - Surface potential issues and blockers
3. **Create Step Plan** - Break down implementation into phases
4. **Wait for Confirmation** - MUST receive user approval before proceeding

## When to Use

Use `/plan` when:
- Starting a new feature
- Making significant architectural changes
- Working on complex refactoring
- Multiple files/components will be affected
- Requirements are unclear or ambiguous

## How It Works

The planner agent will:

1. **Analyze the request** and restate requirements in clear terms
2. **Break down into phases** with specific, actionable steps
3. **Identify dependencies** between components
4. **Assess risks** and potential blockers
5. **Estimate complexity** (High/Medium/Low)
6. **Present the plan** and WAIT for your explicit confirmation

## Example Usage

```
User: /plan I need to add real-time notifications when markets resolve

Agent (planner):
# Implementation Plan: Real-Time Market Resolution Notifications

## Requirements Restatement
- Send notifications to users when markets they're watching resolve
- Support multiple notification channels (in-app, email, webhook)
- Ensure notifications are delivered reliably
- Include market outcome and user's position result

## Implementation Phases

### Phase 1: Database Schema
- Add notifications table with columns: id, user_id, market_id, type, status, created_at
- Add user_notification_preferences table for channel preferences
- Create indexes on user_id and market_id for performance

### Phase 2: Notification Service
- Create notification service in lib/notifications.ts
- Implement notification queue using BullMQ/Redis
- Add retry logic for failed deliveries
- Create notification templates

### Phase 3: Integration Points
- Hook into market resolution logic (when status changes to "resolved")
- Query all users with positions in market
- Enqueue notifications for each user

### Phase 4: Frontend Components
- Create NotificationBell component in header
- Add NotificationList modal
- Implement real-time updates via Supabase subscriptions
- Add notification preferences page

## Dependencies
- Redis (for queue)
- Email service (SendGrid/Resend)
- Supabase real-time subscriptions

## Risks
- HIGH: Email deliverability (SPF/DKIM required)
- MEDIUM: Performance with 1000+ users per market
- MEDIUM: Notification spam if markets resolve frequently
- LOW: Real-time subscription overhead

## Estimated Complexity: MEDIUM
- Backend: 4-6 hours
- Frontend: 3-4 hours
- Testing: 2-3 hours
- Total: 9-13 hours

**WAITING FOR CONFIRMATION**: Proceed with this plan? (yes/no/modify)
```

## Important Notes

**CRITICAL**: The planner agent will **NOT** write any code until you explicitly confirm the plan with "yes" or "proceed" or similar affirmative response.

If you want changes, respond with:
- "modify: [your changes]"
- "different approach: [alternative]"
- "skip phase 2 and do phase 3 first"

## Phase 5: Create Issue + Write Ticket Handoff (After Plan Confirmation)

After the user confirms the plan, the planner agent will:

1. Read `.claude/project.json` to determine the configured tracker
2. Create the issue in the tracker using the plan title and a concise summary as the body:
   - **GitHub:** `gh issue create --title "{plan title}" --body "{plan summary}"` (add `--repo {githubRepo}` if set)
     → Capture the returned issue number → ticket ID becomes `GH-{N}`
   - **Linear:** `linear issues create "{plan title}" --team {linearTeam} --description "{plan summary}"` (add `--project "{linearProject}"` if set)
     → Capture the returned issue ID (e.g., `ENG-42`) → use as ticket ID
   - **No tracker (`"none"` or missing config):** Ask the user for the issue number (fallback to previous behavior)
3. Create `.ai/tickets/{ISSUE-ID}/context.md` with the full confirmed plan, all file paths, files to read before starting, and decisions made during planning
4. Set Status to `planning-complete`
5. Write the ticket ID to `.ai/tickets/active.md`
6. Report: "Issue created: {URL}. Ticket context written to `.ai/tickets/{ISSUE-ID}/context.md`. Start implementation with `/tdd {ISSUE-ID}` in a fresh session."

This handoff document enables any agent (Claude, Gemini, or future) to pick up implementation without re-planning.

## Integration with Other Commands

After planning:
- Use `/tdd` to implement with test-driven development (loads ticket context automatically)
- Use `/build-fix` if build errors occur
- Use `/code-review` to review completed implementation

## Related Agents

This command invokes the `planner` agent located at:
`.claude/agents/planner.md`
