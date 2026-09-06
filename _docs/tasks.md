# Backlog

Tasks for building the shared household chore assignment tool described in `plan.md`. Each task is scoped to fit in one working session and is written to be understood on its own, without needing to read any other task first.

## 1. Project scaffolding with a passing test
Goal: Get an empty project running with one passing test.
Description: Set up the project skeleton (framework install, one app/module, base configuration) and add a single trivial test that passes — for example, that the app's health/login page responds successfully. No domain models or business logic yet; this task only proves the toolchain and test runner work end to end.

## 2. Household and Membership models
Goal: Model a household and its members with a permanent join order.
Description: Add a Household record (name, a chosen weekly rotation day) and a Membership record linking a person to a household. Each member gets a sequence number assigned once when they join, which is never reused or renumbered even after someone leaves. Write tests covering sequential assignment across multiple members and marking a member inactive.

## 3. Chore and WeeklyAssignment models
Goal: Model a chore and its per-week assignment record.
Description: Add a Chore record (belongs to a household) and a WeeklyAssignment record that captures who is responsible for a given chore during a given week, plus whether it's done. Each chore keeps its own position in the household's rotation sequence, seeded when the chore is created so that different chores don't all start with the same person. Write tests for the seeding math and for the one-assignment-per-chore-per-week rule.

## 4. Rotation service
Goal: Implement the "whose turn is it" logic as a standalone piece, independent of any screen.
Description: Write the logic that, given a chore, finds the next active member in its rotation sequence — skipping anyone who has left, and wrapping back to the start when it reaches the end. Add a function that advances a household's chores to a new week when one is due, safe to call repeatedly without creating duplicates. Cover wrap-around, skipping removed members, and repeat-call safety with tests; no UI is needed for this task.

## 5. Login, logout, and signup
Goal: Let a person create an account and sign in.
Description: Wire up standard login and logout, plus a signup form for creating a new user account. This task only concerns having an authenticated user session — it does not need to know anything about households yet.

## 6. Household onboarding and access control
Goal: Let a freshly signed-up user create their household, and make sure every later screen can trust "the current user's household."
Description: Add a step where a logged-in user with no household yet can create one, becoming its first member. Add a single reusable check (used by every screen built afterward) that confirms the current user belongs to an active household before showing them anything, and sends them to create one if not.

## 7. This Week screen
Goal: Show the current week's chores and let people mark them done or reassign them.
Description: Build the default landing screen: it rolls the household forward to the current week if needed, then lists each chore with its assignee and status (pending/done). Add two actions on each row — mark the chore done, and manually reassign it to a different active member — that update in place without a full page reload. A manual reassignment only affects the current week; it must not change the chore's underlying rotation position.

## 8. Chores management screen
Goal: Let users add, edit, and delete chores.
Description: Build a screen listing a household's chores with a form to add a new one, and the ability to edit an existing chore's name/description or delete it. Adding a chore must go through the same seeding logic used elsewhere so new chores stagger into the rotation correctly, not just save the row directly.

## 9. Members management screen
Goal: Let users add and remove household members.
Description: Build a screen to add a new member (creating their login) and remove an existing one. Removing someone must not erase history — it deactivates them, unassigns any chore currently pending on them for the active week so it can be manually reassigned, and excludes them from future rotations. Guard against removing yourself or the last remaining active member, since either would lock everyone out of the household with no recovery path.

## 10. Settings screen
Goal: Let users rename the household and change its weekly rotation day.
Description: Build a simple form to edit the household's display name and the day of the week its chores roll over on. Restrict the rotation day to a valid day-of-week value rather than accepting any number.
