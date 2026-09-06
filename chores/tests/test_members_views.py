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
        week_start = current_week_start(self.household)
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

    def test_cannot_remove_self(self):
        bob_user = User.objects.create_user(username="bob", password="pw")
        Membership.objects.create_next(self.household, bob_user)
        response = self.client.post(f"/members/{self.alice.id}/remove/")
        self.assertEqual(response.status_code, 302)
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.is_active)

    def test_cannot_remove_last_active_member(self):
        response = self.client.post(f"/members/{self.alice.id}/remove/")
        self.assertEqual(response.status_code, 302)
        self.alice.refresh_from_db()
        self.assertTrue(self.alice.is_active)
