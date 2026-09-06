# Shared Household Chore Assignment Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Django MVP described in `plan.md` — a shared household chore tool with automatic weekly rotation per chore, manual reassignment, and basic pending/done tracking.

**Architecture:** A single Django project (`config/`) with one app (`chores/`). Server-rendered templates with HTMX for in-page actions (mark done, reassign) — no separate frontend build. SQLite, local dev only. Django's built-in auth for login; a `Membership` model links users to a `Household`. A small `rotation.py` service module owns all rotation-pointer logic, called lazily from the "This Week" view (no scheduler/cron).

**Tech Stack:** Django (pinned `>=5.2,<5.3`), HTMX (vendored as a local static file, served same-origin — no runtime CDN dependency), SQLite, Django's built-in `TestCase` + test client.

**Spec:** `docs/superpowers/specs/2026-09-06-django-chore-app-design.md`

## Global Constraints

- Django version pinned to `>=5.2,<5.3` in `requirements.txt`.
- No frontend build tooling — HTMX vendored as a local static file (fetched once at setup time and committed), served same-origin; no `<script src>` pointed at a third-party CDN at runtime, plain Django templates.
- SQLite only, local development — no deployment/hosting configuration.
- Django's built-in `User` model and auth views — no custom user model, no third-party auth package.
- Single Django app named `chores` — do not split into multiple apps.
- Tests use Django's built-in `TestCase` and test client only — no pytest, no factory libraries.
- `Membership.rotation_order` values are assigned once at join time and are **never** renumbered or reused.
- Manual reassignment (`WeeklyAssignment.assigned_member` / `is_manual_override`) must never modify `Chore.last_rotation_order`.
- All household-scoped views must 404 (not redirect or 403) on cross-household access attempts.

---

## Task 1: Project Scaffolding

**Files:**
- Create: `manage.py`, `config/__init__.py`, `config/settings.py`, `config/urls.py`, `config/wsgi.py`, `config/asgi.py` (via `django-admin startproject`)
- Create: `chores/__init__.py`, `chores/apps.py`, `chores/models.py`, `chores/admin.py`, `chores/views.py`, `chores/migrations/__init__.py` (via `manage.py startapp`)
- Create: `chores/templates/base.html`
- Create: `chores/static/chores/htmx.min.js` (vendored, fetched via `curl`)
- Create: `chores/tests/__init__.py`, `chores/tests/test_project_setup.py`
- Create: `requirements.txt`, `.gitignore`
- Modify: `config/settings.py`

**Interfaces:**
- Consumes: nothing (first task)
- Produces: a working Django project with the `chores` app installed; `base.html` template block structure (`{% block title %}`, `{% block content %}`) that all later templates extend; a vendored `htmx.min.js` served from Django's static files (same-origin, no CDN dependency at runtime).

- [ ] **Step 1: Create `requirements.txt`**

```text
Django>=5.2,<5.3
```

- [ ] **Step 2: Install and scaffold the project**

Run:
```bash
pip install -r requirements.txt
django-admin startproject config .
python manage.py startapp chores
mkdir -p chores/tests
touch chores/tests/__init__.py
rm chores/tests.py
```

(`startapp` creates a `chores/tests.py` stub — remove it since we're using a `chores/tests/` package instead.)

- [ ] **Step 3: Wire up the `chores` app in settings**

Modify `config/settings.py` — add `"chores"` to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "chores",
]
```

- [ ] **Step 4: Vendor htmx as a local static file**

Fetch a pinned version of htmx once and commit it to the repo, rather than loading it from a CDN at runtime (avoids depending on third-party CDN availability/integrity at request time):

```bash
mkdir -p chores/static/chores
curl -o chores/static/chores/htmx.min.js https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js
```

Verify the file downloaded and is non-trivial in size (htmx 1.9.12 is roughly 45 KB):

Run: `wc -c chores/static/chores/htmx.min.js`
Expected: a byte count in the tens of thousands (not 0, not an HTML error page)

- [ ] **Step 5: Create the base template**

Create `chores/templates/base.html`:

```html
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{% block title %}Household Chores{% endblock %}</title>
  <script src="{% static 'chores/htmx.min.js' %}"></script>
</head>
<body>
  {% block content %}{% endblock %}
</body>
</html>
```

- [ ] **Step 6: Create `.gitignore`**

```text
__pycache__/
*.pyc
db.sqlite3
.venv/
```

- [ ] **Step 7: Write the smoke test**

Create `chores/tests/test_project_setup.py`:

```python
from django.test import TestCase


class ProjectSetupTests(TestCase):
    def test_admin_login_page_loads(self):
        response = self.client.get("/admin/login/")
        self.assertEqual(response.status_code, 200)
```

- [ ] **Step 8: Verify the project boots and the test passes**

Run: `python manage.py check`
Expected: `System check identified no issues`

Run: `python manage.py test chores.tests.test_project_setup`
Expected: `OK` (1 test passes)

- [ ] **Step 9: Commit**

```bash
git add manage.py config chores requirements.txt .gitignore
git commit -m "chore: scaffold Django project and chores app"
```

---

## Task 2: Household & Membership Models

**Files:**
- Modify: `chores/models.py`
- Create: `chores/tests/test_models.py`

**Interfaces:**
- Consumes: nothing new
- Produces:
  - `Household(name, rotation_day)`
  - `Membership(user, household, rotation_order, is_active, joined_at, left_at)` with `Membership.objects.create_next(household, user)` and `membership.deactivate()`

- [ ] **Step 1: Write the failing tests**

Create `chores/tests/test_models.py`:

```python
from django.contrib.auth import get_user_model
from django.test import TestCase

from chores.models import Household, Membership

User = get_user_model()


class MembershipTests(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Smith House", rotation_day=0)
        self.alice = User.objects.create_user(username="alice", password="pw")
        self.bob = User.objects.create_user(username="bob", password="pw")

    def test_create_next_assigns_sequential_rotation_order(self):
        m1 = Membership.objects.create_next(self.household, self.alice)
        m2 = Membership.objects.create_next(self.household, self.bob)
        self.assertEqual(m1.rotation_order, 0)
        self.assertEqual(m2.rotation_order, 1)

    def test_rotation_order_is_independent_per_household(self):
        other_household = Household.objects.create(name="Other House", rotation_day=0)
        carol = User.objects.create_user(username="carol", password="pw")
        Membership.objects.create_next(self.household, self.alice)
        m_other = Membership.objects.create_next(other_household, carol)
        self.assertEqual(m_other.rotation_order, 0)

    def test_deactivate_sets_inactive_and_left_at(self):
        membership = Membership.objects.create_next(self.household, self.alice)
        self.assertTrue(membership.is_active)
        self.assertIsNone(membership.left_at)
        membership.deactivate()
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)
        self.assertIsNotNone(membership.left_at)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test chores.tests.test_models -v 2`
Expected: `ImportError` or `AttributeError` — `Household`/`Membership` not defined yet.

- [ ] **Step 3: Implement the models**

Modify `chores/models.py`:

```python
from django.conf import settings
from django.db import models
from django.utils import timezone


class Household(models.Model):
    name = models.CharField(max_length=100)
    rotation_day = models.IntegerField(default=0)  # 0=Monday ... 6=Sunday

    def __str__(self):
        return self.name


class MembershipManager(models.Manager):
    def create_next(self, household, user):
        last = (
            self.filter(household=household)
            .order_by("-rotation_order")
            .first()
        )
        next_order = 0 if last is None else last.rotation_order + 1
        return self.create(household=household, user=user, rotation_order=next_order)


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="memberships")
    rotation_order = models.IntegerField()
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    objects = MembershipManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["household", "rotation_order"],
                name="unique_rotation_order_per_household",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} @ {self.household.name}"

    def deactivate(self):
        self.is_active = False
        self.left_at = timezone.now()
        self.save(update_fields=["is_active", "left_at"])
```

- [ ] **Step 4: Make migrations and run tests**

Run: `python manage.py makemigrations chores`
Expected: a new migration file created for `Household` and `Membership`.

Run: `python manage.py test chores.tests.test_models -v 2`
Expected: `OK` (3 tests pass)

- [ ] **Step 5: Commit**

```bash
git add chores/models.py chores/migrations chores/tests/test_models.py
git commit -m "feat: add Household and Membership models"
```

---

## Task 3: Chore & WeeklyAssignment Models

**Files:**
- Modify: `chores/models.py`
- Modify: `chores/tests/test_models.py`

**Interfaces:**
- Consumes: `Household`, `Membership` (Task 2)
- Produces:
  - `Chore(household, name, description, created_at, last_rotation_order)` with `Chore.objects.create_with_offset(household, name, description="")`
  - `WeeklyAssignment(chore, week_start_date, assigned_member, status, is_manual_override)` with class constants `WeeklyAssignment.PENDING` / `WeeklyAssignment.DONE`

- [ ] **Step 1: Write the failing tests**

Append to `chores/tests/test_models.py`:

```python
from chores.models import Chore, WeeklyAssignment


class ChoreOffsetTests(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Smith House", rotation_day=0)
        self.alice = User.objects.create_user(username="alice", password="pw")
        self.bob = User.objects.create_user(username="bob", password="pw")
        self.carol = User.objects.create_user(username="carol", password="pw")
        self.m_alice = Membership.objects.create_next(self.household, self.alice)
        self.m_bob = Membership.objects.create_next(self.household, self.bob)
        self.m_carol = Membership.objects.create_next(self.household, self.carol)

    def test_first_chore_seeds_offset_at_first_active_member(self):
        chore = Chore.objects.create_with_offset(self.household, "Trash")
        # last_rotation_order must be the max active rotation_order (2, carol's),
        # so the next-assignee lookup wraps to the smallest (0, alice's).
        self.assertEqual(chore.last_rotation_order, self.m_carol.rotation_order)

    def test_second_chore_seeds_offset_one_member_later(self):
        Chore.objects.create_with_offset(self.household, "Trash")
        chore2 = Chore.objects.create_with_offset(self.household, "Bathroom")
        # second chore (existing_count=1) should seed so next-assignee is bob (index 1).
        self.assertEqual(chore2.last_rotation_order, self.m_alice.rotation_order)

    def test_chore_with_no_active_members_seeds_negative_one(self):
        empty_household = Household.objects.create(name="Empty House", rotation_day=0)
        chore = Chore.objects.create_with_offset(empty_household, "Trash")
        self.assertEqual(chore.last_rotation_order, -1)


class WeeklyAssignmentTests(TestCase):
    def test_unique_constraint_one_assignment_per_chore_per_week(self):
        household = Household.objects.create(name="Smith House", rotation_day=0)
        chore = Chore.objects.create(household=household, name="Trash", last_rotation_order=-1)
        WeeklyAssignment.objects.create(
            chore=chore, week_start_date="2026-01-05", status=WeeklyAssignment.PENDING
        )
        with self.assertRaises(Exception):
            WeeklyAssignment.objects.create(
                chore=chore, week_start_date="2026-01-05", status=WeeklyAssignment.PENDING
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test chores.tests.test_models -v 2`
Expected: `ImportError` — `Chore`/`WeeklyAssignment` not defined yet.

- [ ] **Step 3: Implement the models**

Append to `chores/models.py`:

```python
class ChoreManager(models.Manager):
    def create_with_offset(self, household, name, description=""):
        active_orders = list(
            household.memberships.filter(is_active=True)
            .order_by("rotation_order")
            .values_list("rotation_order", flat=True)
        )
        existing_count = self.filter(household=household).count()
        if active_orders:
            n = len(active_orders)
            offset_index = existing_count % n
            seed = active_orders[-1] if offset_index == 0 else active_orders[offset_index - 1]
        else:
            seed = -1
        return self.create(
            household=household,
            name=name,
            description=description,
            last_rotation_order=seed,
        )


class Chore(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="chores")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_rotation_order = models.IntegerField()

    objects = ChoreManager()

    def __str__(self):
        return self.name


class WeeklyAssignment(models.Model):
    PENDING = "pending"
    DONE = "done"
    STATUS_CHOICES = [(PENDING, "Pending"), (DONE, "Done")]

    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name="assignments")
    week_start_date = models.DateField()
    assigned_member = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True, blank=True, related_name="assignments"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    is_manual_override = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["chore", "week_start_date"],
                name="unique_assignment_per_chore_per_week",
            ),
        ]

    def __str__(self):
        return f"{self.chore.name} - {self.week_start_date}"
```

- [ ] **Step 4: Make migrations and run tests**

Run: `python manage.py makemigrations chores`

Run: `python manage.py test chores.tests.test_models -v 2`
Expected: `OK` (6 tests pass)

- [ ] **Step 5: Commit**

```bash
git add chores/models.py chores/migrations chores/tests/test_models.py
git commit -m "feat: add Chore and WeeklyAssignment models"
```

---

## Task 4: Rotation Service

**Files:**
- Create: `chores/rotation.py`
- Create: `chores/tests/test_rotation.py`

**Interfaces:**
- Consumes: `Household`, `Membership`, `Chore`, `WeeklyAssignment` (Tasks 2-3)
- Produces:
  - `next_active_membership(chore) -> Membership | None`
  - `rotate_household(household, week_start_date) -> list[WeeklyAssignment]`
  - `current_week_start(household, today=None) -> date`
  - `ensure_current_week(household, today=None) -> date`

- [ ] **Step 1: Write the failing tests**

Create `chores/tests/test_rotation.py`:

```python
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from chores.models import Chore, Household, Membership, WeeklyAssignment
from chores.rotation import (
    current_week_start,
    ensure_current_week,
    next_active_membership,
    rotate_household,
)

User = get_user_model()


class RotationTests(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Smith House", rotation_day=0)
        self.alice = Membership.objects.create_next(
            self.household, User.objects.create_user(username="alice", password="pw")
        )
        self.bob = Membership.objects.create_next(
            self.household, User.objects.create_user(username="bob", password="pw")
        )
        self.carol = Membership.objects.create_next(
            self.household, User.objects.create_user(username="carol", password="pw")
        )
        self.chore = Chore.objects.create_with_offset(self.household, "Trash")

    def test_next_active_membership_advances_in_order(self):
        # seeded so first assignee is alice (rotation_order 0)
        self.assertEqual(next_active_membership(self.chore), self.alice)
        self.chore.last_rotation_order = self.alice.rotation_order
        self.assertEqual(next_active_membership(self.chore), self.bob)

    def test_next_active_membership_wraps_around(self):
        self.chore.last_rotation_order = self.carol.rotation_order
        self.assertEqual(next_active_membership(self.chore), self.alice)

    def test_next_active_membership_skips_inactive(self):
        self.bob.deactivate()
        self.chore.last_rotation_order = self.alice.rotation_order
        self.assertEqual(next_active_membership(self.chore), self.carol)

    def test_rotate_household_creates_assignment_and_advances_pointer(self):
        week1 = datetime.date(2026, 1, 5)
        assignments = rotate_household(self.household, week1)
        self.assertEqual(len(assignments), 1)
        self.chore.refresh_from_db()
        self.assertEqual(assignments[0].assigned_member, self.alice)
        self.assertEqual(self.chore.last_rotation_order, self.alice.rotation_order)

    def test_rotate_household_is_idempotent_for_same_week(self):
        week1 = datetime.date(2026, 1, 5)
        rotate_household(self.household, week1)
        second_call = rotate_household(self.household, week1)
        self.assertEqual(len(second_call), 0)
        self.assertEqual(
            WeeklyAssignment.objects.filter(chore=self.chore, week_start_date=week1).count(), 1
        )

    def test_manual_reassignment_does_not_move_pointer(self):
        week1 = datetime.date(2026, 1, 5)
        rotate_household(self.household, week1)
        assignment = WeeklyAssignment.objects.get(chore=self.chore, week_start_date=week1)
        assignment.assigned_member = self.carol
        assignment.is_manual_override = True
        assignment.save()
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.last_rotation_order, self.alice.rotation_order)
        week2 = datetime.date(2026, 1, 12)
        rotate_household(self.household, week2)
        assignment2 = WeeklyAssignment.objects.get(chore=self.chore, week_start_date=week2)
        self.assertEqual(assignment2.assigned_member, self.bob)

    def test_current_week_start_aligns_to_rotation_day(self):
        # rotation_day=0 (Monday); 2026-01-08 is a Thursday
        result = current_week_start(self.household, today=datetime.date(2026, 1, 8))
        self.assertEqual(result, datetime.date(2026, 1, 5))

    def test_ensure_current_week_creates_assignment_for_today(self):
        week_start = ensure_current_week(self.household, today=datetime.date(2026, 1, 8))
        self.assertEqual(week_start, datetime.date(2026, 1, 5))
        self.assertTrue(
            WeeklyAssignment.objects.filter(chore=self.chore, week_start_date=week_start).exists()
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test chores.tests.test_rotation -v 2`
Expected: `ModuleNotFoundError: No module named 'chores.rotation'`

- [ ] **Step 3: Implement the rotation service**

Create `chores/rotation.py`:

```python
import datetime

from django.utils import timezone

from .models import WeeklyAssignment


def next_active_membership(chore):
    household = chore.household
    active = list(
        household.memberships.filter(is_active=True).order_by("rotation_order")
    )
    if not active:
        return None
    for membership in active:
        if membership.rotation_order > chore.last_rotation_order:
            return membership
    return active[0]


def rotate_household(household, week_start_date):
    created = []
    for chore in household.chores.all():
        if WeeklyAssignment.objects.filter(
            chore=chore, week_start_date=week_start_date
        ).exists():
            continue
        member = next_active_membership(chore)
        assignment = WeeklyAssignment.objects.create(
            chore=chore,
            week_start_date=week_start_date,
            assigned_member=member,
            status=WeeklyAssignment.PENDING,
        )
        if member is not None:
            chore.last_rotation_order = member.rotation_order
            chore.save(update_fields=["last_rotation_order"])
        created.append(assignment)
    return created


def current_week_start(household, today=None):
    today = today or timezone.localdate()
    days_since_rotation_day = (today.weekday() - household.rotation_day) % 7
    return today - datetime.timedelta(days=days_since_rotation_day)


def ensure_current_week(household, today=None):
    week_start = current_week_start(household, today=today)
    rotate_household(household, week_start)
    return week_start
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test chores.tests.test_rotation -v 2`
Expected: `OK` (8 tests pass)

- [ ] **Step 5: Commit**

```bash
git add chores/rotation.py chores/tests/test_rotation.py
git commit -m "feat: add rotation service module"
```

---

## Task 5: Auth & Household Bootstrap

**Files:**
- Create: `chores/forms.py`
- Create: `chores/decorators.py`
- Modify: `chores/views.py`
- Create: `chores/urls.py`
- Modify: `config/urls.py`
- Modify: `config/settings.py`
- Create: `chores/templates/registration/login.html`
- Create: `chores/templates/chores/signup.html`
- Create: `chores/templates/chores/create_household.html`
- Create: `chores/tests/test_auth.py`

**Interfaces:**
- Consumes: `Household`, `Membership` (Task 2)
- Produces:
  - `get_current_membership(request) -> Membership | None`
  - `household_required` decorator — sets `request.membership` and redirects to `create_household` (URL name) if none
  - URL names: `login`, `logout`, `signup`, `create_household` (all present after this task)

- [ ] **Step 1: Write the failing tests**

Create `chores/tests/test_auth.py`:

```python
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from chores.decorators import get_current_membership, household_required
from chores.models import Household, Membership

User = get_user_model()


class HouseholdRequiredDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username="alice", password="pw")

    def _dummy_view(self, request):
        return HttpResponse(f"household={request.membership.household.name}")

    def test_redirects_to_create_household_when_no_membership(self):
        request = self.factory.get("/")
        request.user = self.user
        wrapped = household_required(self._dummy_view)
        response = wrapped(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/create-household/", response["Location"])

    def test_passes_through_and_sets_request_membership(self):
        household = Household.objects.create(name="Smith House", rotation_day=0)
        Membership.objects.create_next(household, self.user)
        request = self.factory.get("/")
        request.user = self.user
        wrapped = household_required(self._dummy_view)
        response = wrapped(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"household=Smith House")

    def test_get_current_membership_ignores_inactive(self):
        household = Household.objects.create(name="Smith House", rotation_day=0)
        membership = Membership.objects.create_next(household, self.user)
        membership.deactivate()
        request = self.factory.get("/")
        request.user = self.user
        self.assertIsNone(get_current_membership(request))


class SignupAndCreateHouseholdViewTests(TestCase):
    def test_signup_creates_user_and_redirects_to_create_household(self):
        response = self.client.post(
            "/signup/",
            {"username": "alice", "password1": "a-strong-pw-123", "password2": "a-strong-pw-123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/create-household/")
        self.assertTrue(User.objects.filter(username="alice").exists())

    def test_create_household_creates_household_and_membership(self):
        user = User.objects.create_user(username="alice", password="pw")
        self.client.force_login(user)
        response = self.client.post(
            "/create-household/", {"name": "Smith House", "rotation_day": 0}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")
        household = Household.objects.get(name="Smith House")
        self.assertTrue(Membership.objects.filter(household=household, user=user).exists())

    def test_create_household_redirects_away_if_already_a_member(self):
        user = User.objects.create_user(username="alice", password="pw")
        household = Household.objects.create(name="Existing House", rotation_day=0)
        Membership.objects.create_next(household, user)
        self.client.force_login(user)
        response = self.client.get("/create-household/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test chores.tests.test_auth -v 2`
Expected: `ModuleNotFoundError: No module named 'chores.decorators'`

- [ ] **Step 3: Implement decorators, forms, views, urls, settings, templates**

Create `chores/decorators.py`:

```python
from functools import wraps

from django.shortcuts import redirect

from .models import Membership


def get_current_membership(request):
    if not request.user.is_authenticated:
        return None
    return Membership.objects.filter(user=request.user, is_active=True).first()


def household_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        membership = get_current_membership(request)
        if membership is None:
            return redirect("create_household")
        request.membership = membership
        return view_func(request, *args, **kwargs)

    return wrapped
```

Create `chores/forms.py`:

```python
from django import forms

from .models import Household


class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ["name", "rotation_day"]
```

Modify `chores/views.py`:

```python
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from .decorators import get_current_membership
from .forms import HouseholdForm
from .models import Membership


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("create_household")
    else:
        form = UserCreationForm()
    return render(request, "chores/signup.html", {"form": form})


@login_required
def create_household(request):
    if get_current_membership(request) is not None:
        return redirect("/")
    if request.method == "POST":
        form = HouseholdForm(request.POST)
        if form.is_valid():
            household = form.save()
            Membership.objects.create_next(household, request.user)
            return redirect("/")
    else:
        form = HouseholdForm()
    return render(request, "chores/create_household.html", {"form": form})
```

Create `chores/urls.py`:

```python
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("create-household/", views.create_household, name="create_household"),
]
```

Modify `config/urls.py`:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("chores.urls")),
]
```

Modify `config/settings.py` — add at the end:

```python
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "login"
```

Create `chores/templates/registration/login.html`:

```html
{% extends "base.html" %}
{% block title %}Log in{% endblock %}
{% block content %}
<h1>Log in</h1>
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Log in</button>
</form>
<p><a href="{% url 'signup' %}">Sign up</a></p>
{% endblock %}
```

Create `chores/templates/chores/signup.html`:

```html
{% extends "base.html" %}
{% block title %}Sign up{% endblock %}
{% block content %}
<h1>Sign up</h1>
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Sign up</button>
</form>
{% endblock %}
```

Create `chores/templates/chores/create_household.html`:

```html
{% extends "base.html" %}
{% block title %}Create your household{% endblock %}
{% block content %}
<h1>Create your household</h1>
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Create</button>
</form>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test chores.tests.test_auth -v 2`
Expected: `OK` (6 tests pass)

- [ ] **Step 5: Commit**

```bash
git add chores/decorators.py chores/forms.py chores/views.py chores/urls.py config/urls.py config/settings.py chores/templates chores/tests/test_auth.py
git commit -m "feat: add auth, signup, and household bootstrap"
```

---

## Task 6: This Week View

**Files:**
- Modify: `chores/views.py`
- Modify: `chores/urls.py`
- Modify: `chores/templates/base.html`
- Create: `chores/templates/chores/this_week.html`
- Create: `chores/templates/chores/_assignment_row.html`
- Create: `chores/tests/test_this_week.py`

**Interfaces:**
- Consumes: `household_required` (Task 5), `ensure_current_week` (Task 4), `WeeklyAssignment`/`Membership` (Tasks 2-3)
- Produces: URL names `this_week`, `mark_done`, `reassign`

- [ ] **Step 1: Write the failing tests**

Create `chores/tests/test_this_week.py`:

```python
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from chores.models import Chore, Household, Membership, WeeklyAssignment

User = get_user_model()


class ThisWeekViewTests(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Smith House", rotation_day=0)
        self.alice_user = User.objects.create_user(username="alice", password="pw")
        self.bob_user = User.objects.create_user(username="bob", password="pw")
        self.alice = Membership.objects.create_next(self.household, self.alice_user)
        self.bob = Membership.objects.create_next(self.household, self.bob_user)
        self.chore = Chore.objects.create_with_offset(self.household, "Trash")
        self.client.force_login(self.alice_user)

    def test_this_week_creates_and_lists_current_assignment(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trash")
        assignment = WeeklyAssignment.objects.get(chore=self.chore)
        self.assertEqual(assignment.assigned_member, self.alice)

    def test_mark_done_updates_status(self):
        self.client.get("/")  # triggers rotation
        assignment = WeeklyAssignment.objects.get(chore=self.chore)
        response = self.client.post(f"/assignments/{assignment.id}/mark-done/")
        self.assertEqual(response.status_code, 200)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, WeeklyAssignment.DONE)

    def test_reassign_updates_assignee_without_moving_pointer(self):
        self.client.get("/")
        assignment = WeeklyAssignment.objects.get(chore=self.chore)
        response = self.client.post(
            f"/assignments/{assignment.id}/reassign/", {"member_id": self.bob.id}
        )
        self.assertEqual(response.status_code, 200)
        assignment.refresh_from_db()
        self.assertEqual(assignment.assigned_member, self.bob)
        self.assertTrue(assignment.is_manual_override)
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.last_rotation_order, self.alice.rotation_order)

    def test_cross_household_assignment_is_404(self):
        other_household = Household.objects.create(name="Other House", rotation_day=0)
        other_chore = Chore.objects.create_with_offset(other_household, "Vacuum")
        other_assignment = WeeklyAssignment.objects.create(
            chore=other_chore,
            week_start_date=datetime.date(2026, 1, 5),
            status=WeeklyAssignment.PENDING,
        )
        response = self.client.post(f"/assignments/{other_assignment.id}/mark-done/")
        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test chores.tests.test_this_week -v 2`
Expected: `404` on `GET /` (no such URL yet) or `NoReverseMatch`.

- [ ] **Step 3: Implement the view, urls, and templates**

Modify `chores/views.py` — add:

```python
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from .decorators import household_required
from .models import WeeklyAssignment
from .rotation import ensure_current_week


@login_required
@household_required
def this_week(request):
    household = request.membership.household
    week_start = ensure_current_week(household)
    assignments = (
        WeeklyAssignment.objects.filter(chore__household=household, week_start_date=week_start)
        .select_related("chore", "assigned_member__user")
        .order_by("chore__name")
    )
    active_members = household.memberships.filter(is_active=True).select_related("user")
    return render(
        request,
        "chores/this_week.html",
        {"assignments": assignments, "active_members": active_members},
    )


@login_required
@household_required
@require_POST
def mark_done(request, assignment_id):
    household = request.membership.household
    assignment = get_object_or_404(
        WeeklyAssignment, id=assignment_id, chore__household=household
    )
    assignment.status = WeeklyAssignment.DONE
    assignment.save(update_fields=["status"])
    return render(request, "chores/_assignment_row.html", {"assignment": assignment})


@login_required
@household_required
@require_POST
def reassign(request, assignment_id):
    household = request.membership.household
    assignment = get_object_or_404(
        WeeklyAssignment, id=assignment_id, chore__household=household
    )
    member = get_object_or_404(
        Membership, id=request.POST.get("member_id"), household=household, is_active=True
    )
    assignment.assigned_member = member
    assignment.is_manual_override = True
    assignment.save(update_fields=["assigned_member", "is_manual_override"])
    return render(request, "chores/_assignment_row.html", {"assignment": assignment})
```

Modify `chores/views.py` imports — add `Membership` to the `from .models import ...` line so it reads:

```python
from .models import Membership, WeeklyAssignment
```

Modify `chores/urls.py` — add to `urlpatterns`:

```python
    path("", views.this_week, name="this_week"),
    path("assignments/<int:assignment_id>/mark-done/", views.mark_done, name="mark_done"),
    path("assignments/<int:assignment_id>/reassign/", views.reassign, name="reassign"),
```

Modify `chores/templates/base.html` — replace the `<body>` block with:

```html
<body>
  <nav>
    <a href="{% url 'this_week' %}">This Week</a>
    <form method="post" action="{% url 'logout' %}" style="display:inline">
      {% csrf_token %}
      <button type="submit">Logout</button>
    </form>
  </nav>
  {% block content %}{% endblock %}
</body>
```

Create `chores/templates/chores/_assignment_row.html`:

```html
<tr id="assignment-{{ assignment.id }}">
  <td>{{ assignment.chore.name }}</td>
  <td>{% if assignment.assigned_member %}{{ assignment.assigned_member.user.username }}{% else %}Unassigned{% endif %}</td>
  <td>{{ assignment.get_status_display }}</td>
  <td>
    {% if assignment.status != "done" %}
    <form
      hx-post="{% url 'mark_done' assignment.id %}"
      hx-target="#assignment-{{ assignment.id }}"
      hx-swap="outerHTML"
      style="display:inline">
      {% csrf_token %}
      <button type="submit">Mark done</button>
    </form>
    {% endif %}
    <form
      hx-post="{% url 'reassign' assignment.id %}"
      hx-target="#assignment-{{ assignment.id }}"
      hx-swap="outerHTML"
      style="display:inline">
      {% csrf_token %}
      <select name="member_id" onchange="this.form.requestSubmit()">
        {% for member in assignment.chore.household.memberships.all %}
          {% if member.is_active %}
          <option value="{{ member.id }}" {% if assignment.assigned_member_id == member.id %}selected{% endif %}>
            {{ member.user.username }}
          </option>
          {% endif %}
        {% endfor %}
      </select>
    </form>
  </td>
</tr>
```

Create `chores/templates/chores/this_week.html`:

```html
{% extends "base.html" %}
{% block title %}This Week{% endblock %}
{% block content %}
<h1>This Week</h1>
<table>
  <thead>
    <tr><th>Chore</th><th>Assigned</th><th>Status</th><th>Actions</th></tr>
  </thead>
  <tbody id="assignments">
    {% for assignment in assignments %}
      {% include "chores/_assignment_row.html" %}
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test chores.tests.test_this_week -v 2`
Expected: `OK` (4 tests pass)

- [ ] **Step 5: Commit**

```bash
git add chores/views.py chores/urls.py chores/templates chores/tests/test_this_week.py
git commit -m "feat: add This Week view with mark-done and reassign"
```

---

## Task 7: Chores CRUD Screen

**Files:**
- Modify: `chores/forms.py`
- Modify: `chores/views.py`
- Modify: `chores/urls.py`
- Modify: `chores/templates/base.html`
- Create: `chores/templates/chores/chores_list.html`
- Create: `chores/templates/chores/chore_form.html`
- Create: `chores/tests/test_chores_views.py`

**Interfaces:**
- Consumes: `household_required` (Task 5), `Chore.objects.create_with_offset` (Task 3)
- Produces: URL names `chores_list`, `chore_edit`, `chore_delete`

- [ ] **Step 1: Write the failing tests**

Create `chores/tests/test_chores_views.py`:

```python
from django.contrib.auth import get_user_model
from django.test import TestCase

from chores.models import Chore, Household, Membership

User = get_user_model()


class ChoresCrudViewTests(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Smith House", rotation_day=0)
        self.user = User.objects.create_user(username="alice", password="pw")
        Membership.objects.create_next(self.household, self.user)
        self.client.force_login(self.user)

    def test_add_chore_via_post(self):
        response = self.client.post("/chores/", {"name": "Trash", "description": ""})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Chore.objects.filter(household=self.household, name="Trash").exists())

    def test_chores_list_shows_existing_chores(self):
        Chore.objects.create_with_offset(self.household, "Trash")
        response = self.client.get("/chores/")
        self.assertContains(response, "Trash")

    def test_edit_chore_updates_name(self):
        chore = Chore.objects.create_with_offset(self.household, "Trash")
        response = self.client.post(
            f"/chores/{chore.id}/edit/", {"name": "Take out trash", "description": ""}
        )
        self.assertEqual(response.status_code, 302)
        chore.refresh_from_db()
        self.assertEqual(chore.name, "Take out trash")

    def test_delete_chore_removes_it(self):
        chore = Chore.objects.create_with_offset(self.household, "Trash")
        response = self.client.post(f"/chores/{chore.id}/delete/")
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Chore.objects.filter(id=chore.id).exists())

    def test_cross_household_chore_edit_is_404(self):
        other_household = Household.objects.create(name="Other House", rotation_day=0)
        other_chore = Chore.objects.create_with_offset(other_household, "Vacuum")
        response = self.client.post(
            f"/chores/{other_chore.id}/edit/", {"name": "Hacked", "description": ""}
        )
        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test chores.tests.test_chores_views -v 2`
Expected: `404` (no `/chores/` URL yet).

- [ ] **Step 3: Implement forms, views, urls, templates**

Modify `chores/forms.py` — add:

```python
from .models import Chore


class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ["name", "description"]
```

Modify `chores/views.py` — add:

```python
from .forms import ChoreForm
from .models import Chore


@login_required
@household_required
def chores_list(request):
    household = request.membership.household
    if request.method == "POST":
        form = ChoreForm(request.POST)
        if form.is_valid():
            Chore.objects.create_with_offset(
                household,
                form.cleaned_data["name"],
                description=form.cleaned_data["description"],
            )
            return redirect("chores_list")
    else:
        form = ChoreForm()
    chores = household.chores.all().order_by("name")
    return render(request, "chores/chores_list.html", {"chores": chores, "form": form})


@login_required
@household_required
def chore_edit(request, chore_id):
    household = request.membership.household
    chore = get_object_or_404(Chore, id=chore_id, household=household)
    if request.method == "POST":
        form = ChoreForm(request.POST, instance=chore)
        if form.is_valid():
            form.save()
            return redirect("chores_list")
    else:
        form = ChoreForm(instance=chore)
    return render(request, "chores/chore_form.html", {"form": form, "chore": chore})


@login_required
@household_required
@require_POST
def chore_delete(request, chore_id):
    household = request.membership.household
    chore = get_object_or_404(Chore, id=chore_id, household=household)
    chore.delete()
    return redirect("chores_list")
```

Modify `chores/urls.py` — add to `urlpatterns`:

```python
    path("chores/", views.chores_list, name="chores_list"),
    path("chores/<int:chore_id>/edit/", views.chore_edit, name="chore_edit"),
    path("chores/<int:chore_id>/delete/", views.chore_delete, name="chore_delete"),
```

Modify `chores/templates/base.html` — add a Chores link to `<nav>` right after "This Week":

```html
    <a href="{% url 'chores_list' %}">Chores</a>
```

Create `chores/templates/chores/chores_list.html`:

```html
{% extends "base.html" %}
{% block title %}Chores{% endblock %}
{% block content %}
<h1>Chores</h1>
<ul>
  {% for chore in chores %}
    <li>
      {{ chore.name }}
      <a href="{% url 'chore_edit' chore.id %}">Edit</a>
      <form method="post" action="{% url 'chore_delete' chore.id %}" style="display:inline">
        {% csrf_token %}
        <button type="submit">Delete</button>
      </form>
    </li>
  {% endfor %}
</ul>
<h2>Add a chore</h2>
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Add</button>
</form>
{% endblock %}
```

Create `chores/templates/chores/chore_form.html`:

```html
{% extends "base.html" %}
{% block title %}Edit {{ chore.name }}{% endblock %}
{% block content %}
<h1>Edit chore</h1>
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Save</button>
</form>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test chores.tests.test_chores_views -v 2`
Expected: `OK` (5 tests pass)

- [ ] **Step 5: Commit**

```bash
git add chores/forms.py chores/views.py chores/urls.py chores/templates chores/tests/test_chores_views.py
git commit -m "feat: add Chores CRUD screen"
```

---

## Task 8: Members Screen

**Files:**
- Modify: `chores/views.py`
- Modify: `chores/urls.py`
- Modify: `chores/templates/base.html`
- Create: `chores/templates/chores/members_list.html`
- Create: `chores/tests/test_members_views.py`

**Interfaces:**
- Consumes: `household_required` (Task 5), `Membership.objects.create_next`/`deactivate` (Task 2), `current_week_start` (Task 4)
- Produces: URL names `members_list`, `member_remove`

- [ ] **Step 1: Write the failing tests**

Create `chores/tests/test_members_views.py`:

```python
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from chores.models import Chore, Household, Membership, WeeklyAssignment
from chores.rotation import current_week_start

User = get_user_model()


class MembersViewTests(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Smith House", rotation_day=0)
        self.alice_user = User.objects.create_user(username="alice", password="pw")
        self.alice = Membership.objects.create_next(self.household, self.alice_user)
        self.client.force_login(self.alice_user)

    def test_add_member_creates_user_and_membership(self):
        response = self.client.post(
            "/members/",
            {"username": "bob", "password1": "a-strong-pw-123", "password2": "a-strong-pw-123"},
        )
        self.assertEqual(response.status_code, 302)
        bob_membership = Membership.objects.get(household=self.household, user__username="bob")
        self.assertEqual(bob_membership.rotation_order, 1)

    def test_members_list_shows_members(self):
        response = self.client.get("/members/")
        self.assertContains(response, "alice")

    def test_remove_member_deactivates_and_unassigns_current_week(self):
        bob_user = User.objects.create_user(username="bob", password="pw")
        bob = Membership.objects.create_next(self.household, bob_user)
        chore = Chore.objects.create(household=self.household, name="Trash", last_rotation_order=-1)
        week_start = current_week_start(self.household, today=datetime.date(2026, 1, 8))
        assignment = WeeklyAssignment.objects.create(
            chore=chore, week_start_date=week_start, assigned_member=bob,
            status=WeeklyAssignment.PENDING,
        )
        response = self.client.post(f"/members/{bob.id}/remove/")
        self.assertEqual(response.status_code, 302)
        bob.refresh_from_db()
        self.assertFalse(bob.is_active)
        assignment.refresh_from_db()
        self.assertIsNone(assignment.assigned_member)

    def test_cross_household_member_remove_is_404(self):
        other_household = Household.objects.create(name="Other House", rotation_day=0)
        other_user = User.objects.create_user(username="carol", password="pw")
        other_membership = Membership.objects.create_next(other_household, other_user)
        response = self.client.post(f"/members/{other_membership.id}/remove/")
        self.assertEqual(response.status_code, 404)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test chores.tests.test_members_views -v 2`
Expected: `404` (no `/members/` URL yet).

- [ ] **Step 3: Implement views, urls, templates**

Modify `chores/views.py` — add:

```python
from .models import Membership, WeeklyAssignment
from .rotation import current_week_start


@login_required
@household_required
def members_list(request):
    household = request.membership.household
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            Membership.objects.create_next(household, new_user)
            return redirect("members_list")
    else:
        form = UserCreationForm()
    memberships = household.memberships.all().order_by("rotation_order")
    return render(request, "chores/members_list.html", {"memberships": memberships, "form": form})


@login_required
@household_required
@require_POST
def member_remove(request, membership_id):
    household = request.membership.household
    membership = get_object_or_404(
        Membership, id=membership_id, household=household, is_active=True
    )
    membership.deactivate()
    week_start = current_week_start(household)
    WeeklyAssignment.objects.filter(
        assigned_member=membership,
        week_start_date=week_start,
        status=WeeklyAssignment.PENDING,
    ).update(assigned_member=None)
    return redirect("members_list")
```

(`UserCreationForm` is already imported in `chores/views.py` from Task 5; `Membership` and `get_object_or_404` are already imported from Tasks 5-6 — add `WeeklyAssignment` and `current_week_start` alongside the existing imports rather than duplicating import lines.)

Modify `chores/urls.py` — add to `urlpatterns`:

```python
    path("members/", views.members_list, name="members_list"),
    path("members/<int:membership_id>/remove/", views.member_remove, name="member_remove"),
```

Modify `chores/templates/base.html` — add a Members link to `<nav>` right after "Chores":

```html
    <a href="{% url 'members_list' %}">Members</a>
```

Create `chores/templates/chores/members_list.html`:

```html
{% extends "base.html" %}
{% block title %}Members{% endblock %}
{% block content %}
<h1>Members</h1>
<ul>
  {% for membership in memberships %}
    <li>
      {{ membership.user.username }}
      {% if not membership.is_active %}(removed){% endif %}
      {% if membership.is_active %}
      <form method="post" action="{% url 'member_remove' membership.id %}" style="display:inline">
        {% csrf_token %}
        <button type="submit">Remove</button>
      </form>
      {% endif %}
    </li>
  {% endfor %}
</ul>
<h2>Add a member</h2>
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Add</button>
</form>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test chores.tests.test_members_views -v 2`
Expected: `OK` (4 tests pass)

- [ ] **Step 5: Commit**

```bash
git add chores/views.py chores/urls.py chores/templates chores/tests/test_members_views.py
git commit -m "feat: add Members screen"
```

---

## Task 9: Settings Screen

**Files:**
- Modify: `chores/views.py`
- Modify: `chores/urls.py`
- Modify: `chores/templates/base.html`
- Create: `chores/templates/chores/settings.html`
- Create: `chores/tests/test_settings_view.py`

**Interfaces:**
- Consumes: `household_required` (Task 5), `HouseholdForm` (Task 5), `current_week_start` (Task 4)
- Produces: URL name `household_settings`

- [ ] **Step 1: Write the failing tests**

Create `chores/tests/test_settings_view.py`:

```python
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from chores.models import Household, Membership
from chores.rotation import current_week_start

User = get_user_model()


class SettingsViewTests(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Smith House", rotation_day=0)
        self.user = User.objects.create_user(username="alice", password="pw")
        Membership.objects.create_next(self.household, self.user)
        self.client.force_login(self.user)

    def test_settings_shows_current_household_name(self):
        response = self.client.get("/settings/")
        self.assertContains(response, "Smith House")

    def test_settings_updates_name_and_rotation_day(self):
        response = self.client.post(
            "/settings/", {"name": "Jones House", "rotation_day": 2}
        )
        self.assertEqual(response.status_code, 302)
        self.household.refresh_from_db()
        self.assertEqual(self.household.name, "Jones House")
        self.assertEqual(self.household.rotation_day, 2)
        # rotation_day=2 (Wednesday); 2026-01-08 is a Thursday
        result = current_week_start(self.household, today=datetime.date(2026, 1, 8))
        self.assertEqual(result, datetime.date(2026, 1, 7))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test chores.tests.test_settings_view -v 2`
Expected: `404` (no `/settings/` URL yet).

- [ ] **Step 3: Implement view, urls, template**

Modify `chores/views.py` — add:

```python
@login_required
@household_required
def household_settings(request):
    household = request.membership.household
    if request.method == "POST":
        form = HouseholdForm(request.POST, instance=household)
        if form.is_valid():
            form.save()
            return redirect("household_settings")
    else:
        form = HouseholdForm(instance=household)
    return render(request, "chores/settings.html", {"form": form})
```

Modify `chores/urls.py` — add to `urlpatterns`:

```python
    path("settings/", views.household_settings, name="household_settings"),
```

Modify `chores/templates/base.html` — add a Settings link to `<nav>` right after "Members":

```html
    <a href="{% url 'household_settings' %}">Settings</a>
```

Create `chores/templates/chores/settings.html`:

```html
{% extends "base.html" %}
{% block title %}Settings{% endblock %}
{% block content %}
<h1>Settings</h1>
<form method="post">
  {% csrf_token %}
  {{ form.as_p }}
  <button type="submit">Save</button>
</form>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test chores.tests.test_settings_view -v 2`
Expected: `OK` (2 tests pass)

- [ ] **Step 5: Run the full test suite**

Run: `python manage.py test`
Expected: `OK` (all tests across all task test files pass)

- [ ] **Step 6: Commit**

```bash
git add chores/views.py chores/urls.py chores/templates chores/tests/test_settings_view.py
git commit -m "feat: add Settings screen"
```
