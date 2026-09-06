import datetime

from django.db.models import Max
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
    latest = WeeklyAssignment.objects.filter(
        chore__household=household
    ).aggregate(latest=Max("week_start_date"))["latest"]
    if latest is not None and week_start < latest + datetime.timedelta(days=7):
        return latest
    rotate_household(household, week_start)
    return week_start
