# Architecture

Shared household chore assignment tool — Django MVP. See `plan.md` for the product spec and `docs/superpowers/specs/2026-09-06-django-chore-app-design.md` for the full design rationale. This document describes the system as built.

## Stack

- **Django** (`>=5.2,<5.3`), server-rendered templates.
- **HTMX**, vendored locally at `chores/static/chores/htmx.min.js` (no CDN dependency, no JS build step).
- **SQLite**, local development only — no deployment configuration.
- Django's built-in **auth** (`User` model, `django.contrib.auth` views for login/logout).
- Single app: `chores/`.

## Project layout

```
config/             Django project package (settings, root urlconf)
chores/             the one app — all domain logic lives here
  models.py         Household, Membership, Chore, WeeklyAssignment
  rotation.py       rotation-pointer service (pure-ish functions, no views)
  decorators.py     get_current_membership / household_required
  forms.py          HouseholdForm, ChoreForm (plain ModelForms)
  views.py          all 13 views (auth + 4 screens)
  urls.py           all routes except /admin/
  admin.py          registers all 4 models
  templates/
    base.html                      shared shell + nav, HTMX script tag
    registration/login.html        Django auth's default template name
    chores/*.html                  one template per screen + shared partial
  static/chores/htmx.min.js        vendored dependency
  tests/            one file per task, all Django TestCase + test client
```

## Data model

```
Household(name, rotation_day)
  │ 1
  │
  ├─< Membership(user, household, rotation_order, is_active, joined_at, left_at)
  │       rotation_order: assigned once at join time via Membership.objects.create_next,
  │       never renumbered or reused — this is the household's permanent join-order sequence.
  │
  └─< Chore(household, name, description, last_rotation_order)
          last_rotation_order: this chore's own pointer into the household's rotation_order
          sequence. Independent per chore — seeded at creation (Chore.objects.create_with_offset)
          so different chores start at different points in the same member sequence.
              │
              └─< WeeklyAssignment(chore, week_start_date, assigned_member, status, is_manual_override)
                      one row per chore per week (unique on chore+week_start_date).
                      assigned_member is nullable — null means "unassigned, needs manual reassignment"
                      (the state produced by removing a member mid-cycle).
```

Both `Membership.rotation_order` and `Chore.last_rotation_order` are plain integers, not foreign keys to "current position" — the rotation service (below) does the pointer arithmetic.

## Rotation service (`chores/rotation.py`)

This module owns all pointer logic. Views never touch `last_rotation_order` directly.

- **`next_active_membership(chore)`** — the core rule. Finds the active `Membership` with the smallest `rotation_order` strictly greater than the chore's `last_rotation_order`; wraps to the smallest active `rotation_order` if none is greater. Skipping removed members and welcoming new ones both fall out of this one rule for free — no separate "handle removal" or "handle new member" branch anywhere.

- **`rotate_household(household, week_start_date)`** — for every chore in the household, if it doesn't already have a `WeeklyAssignment` for `week_start_date`, creates one via `next_active_membership` and advances `last_rotation_order` to match. Idempotent per chore: safe to call repeatedly for the same week, and (this matters) still fills in a chore that's missing this week's row even if other chores already have theirs — e.g. a chore added after this week's rotation already ran.

- **`current_week_start(household, today=None)`** — pure date arithmetic: the most recent occurrence of `household.rotation_day` on or before `today`.

- **`ensure_current_week(household, today=None)`** — the lazy trigger, called at the top of every household-scoped view. No cron/scheduler exists; this function IS the scheduler, run on-demand per request. It anchors to the household's latest stored `week_start_date` (via `Max` aggregation) so that changing `rotation_day` mid-cycle doesn't immediately trigger an extra, disruptive rotation — see **Known limitation** below for a gap this introduced.

**Manual reassignment never touches `last_rotation_order`.** The `reassign` view only writes `WeeklyAssignment.assigned_member` / `is_manual_override`. This is enforced by construction — those fields live on a different model than the pointer, and no code path connects them — not by a runtime check.

## Auth & household scoping

- `chores/decorators.py`: `get_current_membership(request)` returns the caller's active `Membership`, or `None`. `household_required` wraps a view, setting `request.membership` or redirecting to `create_household` if the user has none.
- Every household-scoped view stacks `@login_required` (outer) then `@household_required` (inner) then optionally `@require_POST`. This order matters: an anonymous user must hit `login_required` first (→ redirected to `/login/`), not `household_required` (→ would otherwise redirect to `/create-household/`, the wrong place for someone who isn't even logged in).
- **Every** id-parameterized lookup across all 4 screens is scoped with `get_object_or_404(Model, id=..., household=household)` (or the equivalent chore/membership FK chain) — never fetch-then-compare. A cross-household access attempt 404s; it never redirects or 403s. This was independently verified end-to-end in the final review.
- There is no invite/join flow (out of scope per spec) — a user with no membership can only create a brand-new household, not join an existing one. `member_remove` therefore guards against removing yourself or the last active member (added in the final fix wave), since either would permanently lock the household with no recovery path other than Django admin.

## Screens (`chores/views.py`, one view per screen plus two HTMX partial endpoints)

| Screen | View(s) | Notes |
|---|---|---|
| This Week (default, `/`) | `this_week`, `mark_done`, `reassign` | `this_week` calls `ensure_current_week` before querying. `mark_done`/`reassign` are POST-only and return the `_assignment_row.html` partial directly — that partial is also `{% include %}`d from the full page, so it must render correctly standalone (no dependency on `this_week`'s own template context). |
| Chores (`/chores/`) | `chores_list`, `chore_edit`, `chore_delete` | New chores are created via `Chore.objects.create_with_offset`, never a bare `ModelForm.save()`, so the offset-seeding logic always runs. |
| Members (`/members/`) | `members_list`, `member_remove` | Adding a member creates a brand-new `User` (via `UserCreationForm`) + `Membership` in one step — there's no "invite an existing user" path. Removing sets `is_active=False` and unassigns that member's current-week pending chore(s); it never deletes the row (preserves rotation history). |
| Settings (`/settings/`) | `household_settings` | Edits `household.name` / `household.rotation_day` via the same `HouseholdForm` used at household-creation time. `rotation_day` is a `choices` field (0=Monday…6=Sunday), so out-of-range values are rejected by Django's form validation. |

`base.html` carries the nav (This Week / Chores / Members / Settings / Logout) and the vendored HTMX `<script>` tag; every leaf template extends it.

## Testing

Django's built-in `TestCase` + test client throughout, one file per implementation task (`chores/tests/test_*.py`), 48 tests total, all exercising a real SQLite test database — no mocks. `chores/tests/test_login_required.py` specifically asserts anonymous access to all 9 household-scoped URLs redirects to `/login/`.

## Known limitations (accepted for this MVP's scope)

These were surfaced during the final whole-branch review and ruled acceptable given the stated scope (SQLite, local dev, single low-traffic household, no deployment target) — see the SDD ledger at `.superpowers/sdd/2026-09-06-django-chore-app/progress.md` for the full reasoning behind each:

- **No transaction wrapping** around `Membership.objects.create_next`, `Chore.objects.create_with_offset`, or `rotate_household`'s per-chore loop. Concurrent requests can race; the outcomes are either a loud `IntegrityError` (guarded by unique constraints) or, in one case (`create_with_offset`), a silent cosmetic drift in chore-staggering — never data corruption. Not worth `select_for_update()`/`atomic()` overhead at this scale.
- **`DEBUG=True` and a committed `SECRET_KEY`** in `config/settings.py` are Django's stock `startproject` output — fine for local-only use, would need addressing before any deployment.
- **Deleting and re-adding chores can collapse the staggering invariant** (`Chore.objects.create_with_offset`'s seed formula depends on `Chore.objects.filter(household=household).count()`, which changes on delete). Cosmetic only — doesn't affect correctness of who's assigned, just how varied the stagger looks over time.
