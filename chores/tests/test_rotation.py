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

    def test_new_member_not_eligible_until_next_rotation(self):
        week1 = datetime.date(2026, 1, 5)
        rotate_household(self.household, week1)
        User.objects.create_user(username="dave", password="pw")
        current = WeeklyAssignment.objects.get(chore=self.chore, week_start_date=week1)
        self.assertEqual(current.assigned_member, self.alice)
        week2 = datetime.date(2026, 1, 12)
        rotate_household(self.household, week2)
        next_assignment = WeeklyAssignment.objects.get(chore=self.chore, week_start_date=week2)
        self.assertEqual(next_assignment.assigned_member, self.bob)

    def test_removed_member_is_skipped_in_subsequent_rotation(self):
        week1 = datetime.date(2026, 1, 5)
        rotate_household(self.household, week1)
        self.bob.deactivate()
        week2 = datetime.date(2026, 1, 12)
        rotate_household(self.household, week2)
        assignment2 = WeeklyAssignment.objects.get(chore=self.chore, week_start_date=week2)
        self.assertEqual(assignment2.assigned_member, self.carol)

    def test_rotation_day_change_mid_week_does_not_trigger_early_rotation(self):
        week1 = datetime.date(2026, 1, 5)
        ensure_current_week(self.household, today=week1)
        assignment = WeeklyAssignment.objects.get(chore=self.chore, week_start_date=week1)
        assignment.status = WeeklyAssignment.DONE
        assignment.save()
        self.household.rotation_day = 2
        self.household.save()
        thursday_same_week = datetime.date(2026, 1, 8)
        result_week_start = ensure_current_week(self.household, today=thursday_same_week)
        self.assertEqual(result_week_start, week1)
        assignment.refresh_from_db()
        self.assertEqual(assignment.status, WeeklyAssignment.DONE)
