# Shared Household Chore Assignment Tool — Design Spec

Source product spec: `plan.md` (repo root).

## 1. Tech Stack & Project Structure

- **Django** (latest stable), server-rendered templates.
- **HTMX** for in-page actions (mark chore done, reassign) — partial page updates, no full reload, no separate JS build/frontend framework.
- **SQLite**, local development only. No deployment configuration in this iteration.
- **Django's built-in auth** (`User` model) for login/logout.
- Single Django app (`chores/`) — the domain is small enough that splitting into multiple apps would add indirection without benefit.
- **Testing**: Django's built-in test framework (`TestCase` + Django test client). No additional testing tooling.

## 2. Data Model

### Household
- `name`
- `rotation_day`: integer 0–6 (e.g. Monday=0), the weekly day assignments roll over.

### Membership
Links a `User` to a `Household`.
- `user`: FK to `User`
- `household`: FK to `Household`
- `rotation_order`: integer, assigned sequentially at join time within the household, **never reused or renumbered**. Establishes a permanent join-order sequence across everyone who has ever belonged to the household, active or removed.
- `is_active`: boolean, default `True`. Set to `False` on removal — the row is never deleted, preserving rotation history and past `WeeklyAssignment` references.
- `joined_at`: datetime, auto-set.
- `left_at`: datetime, nullable, set on removal.

### Chore
- `household`: FK to `Household`
- `name`
- `description`: optional text
- `created_at`: datetime, auto-set
- `last_rotation_order`: integer. Points at the `rotation_order` of the `Membership` most recently assigned to this chore. This is the chore's independent rotation pointer (see Section 3).

### WeeklyAssignment
One row per chore per week.
- `chore`: FK to `Chore`
- `week_start_date`: date, the Monday-equivalent boundary for that household's rotation cycle
- `assigned_member`: FK to `Membership`, nullable (`null` = unassigned, requires manual reassignment)
- `status`: `pending` | `done`
- `is_manual_override`: boolean, default `False` — set `True` when a household member manually reassigns this week's chore

Unique constraint: (`chore`, `week_start_date`).

## 3. Rotation Algorithm & Trigger

### Trigger: lazy, on-demand (no scheduler)

Every request to a household-scoped view (primarily "This Week") checks whether `today >= household's next rotation date` (derived from the most recent `week_start_date` present for the household + 7 days, aligned to `rotation_day`). If so, the rotation step below runs for every chore in the household **before** the view renders, advancing the household to the new week.

### Rotation step (per chore, per rotation event)

1. Find the active `Membership` in the household with the smallest `rotation_order` **strictly greater** than the chore's current `last_rotation_order`. If none exists (wrapped past the highest `rotation_order`), wrap around to the active `Membership` with the smallest `rotation_order` overall.
2. Create a new `WeeklyAssignment`: `chore`, new `week_start_date`, `assigned_member` = the membership found in step 1, `status='pending'`, `is_manual_override=False`.
3. Update `Chore.last_rotation_order` to that membership's `rotation_order`.

This means each chore tracks its own position in the shared household rotation order — independent of other chores.

### New chore initial offset

When a chore is created, its `last_rotation_order` is seeded (not zero/null) so that its **first** computed assignment lands on the active member at position:

```
(number of chores already existing in the household) mod (number of active members)
```

within the rotation order. This staggers chores from creation, e.g. `Trash: A→B→C`, `Bathroom: B→C→A`, `Vacuum: C→A→B`, rather than every chore starting with the same person.

### Manual reassignment

Updates only the current week's `WeeklyAssignment.assigned_member` (and sets `is_manual_override=True`). It **never** touches `Chore.last_rotation_order`. The next scheduled rotation proceeds from wherever the pointer already was, ignoring the override — matching plan rule 9 (manual reassignment is a temporary exception, not a rotation-history event).

### Member removal

- `Membership.is_active` set to `False`, `left_at` set.
- Any `WeeklyAssignment` for the current week that is still `pending` and assigned to this membership has `assigned_member` set to `None` (unassigned; any member can manually reassign it from "This Week").
- The removed membership's `rotation_order` is simply skipped forever after by the "next active member" lookup in the rotation step — no other pointers need to change.

### New member joining

- A new `Membership` is created with the next `rotation_order` value in the household.
- Current-week `WeeklyAssignment` rows are untouched (plan rule 11: no reshuffling of active assignments).
- The new member becomes eligible starting from the next rotation event, since the rotation step only runs once per household rotation cycle and always operates on the active membership set at that time.

## 4. Screens / Views

All views are scoped to the logged-in user's household via their `Membership`; a user cannot view or act on another household's data (returns 404).

1. **This Week** (`/`, default view) — runs the lazy rotation check, then lists each chore with: assigned member, status (Pending/Done), a "Mark done" action, and a "Reassign" control (dropdown of active members). Both actions are HTMX partial updates.
2. **Chores** (`/chores/`) — list, add, edit, delete chores (standard Django `ModelForm`s).
3. **Members** (`/members/`) — list members; add a member (creates `User` + `Membership`); remove a member (deactivates `Membership` and unassigns their pending current-week chores, per Section 3).
4. **Settings** (`/settings/`) — edit household name and rotation day.

### Auth / onboarding

Standard Django auth views handle login/logout. The plan doesn't specify a signup/invite flow, so onboarding is kept minimal: a user with no `Membership` is prompted to create a new household (becoming its first member) — there is no invite-link flow in this iteration.

## 5. Testing & Error Handling

- **Model/logic tests**: rotation offset seeding on chore creation; skipping inactive members and wrap-around in the rotation step; manual reassignment leaving `last_rotation_order` untouched; member removal unassigning current-week pending chores; new member becoming eligible only from the next rotation.
- **View tests**: each of the four screens renders correctly; household scoping is enforced (cross-household access attempts 404); HTMX endpoints return the expected partial fragment.
- **Error handling**: standard Django form validation (e.g. non-empty chore/member names); 404 for cross-household access. No additional error states are needed given the MVP's scope.

## Out of Scope (carried from plan.md)

Points, rewards, streaks, reminders, notifications, chore difficulty weighting, workload optimization, availability calendars, member preferences, automatic swapping, voting, comments, chat, analytics, multiple chore frequencies, AI-based assignment, household expense tracking, deployment/hosting configuration, invite-based household joining.
