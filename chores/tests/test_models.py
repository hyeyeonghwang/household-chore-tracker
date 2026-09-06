from django.contrib.auth import get_user_model
from django.test import TestCase

from chores.models import Chore, Household, Membership, WeeklyAssignment

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
