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
