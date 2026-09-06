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

    def test_mark_done_returns_assignment_row_partial(self):
        self.client.get("/")
        assignment = WeeklyAssignment.objects.get(chore=self.chore)
        response = self.client.post(f"/assignments/{assignment.id}/mark-done/")
        self.assertTemplateUsed(response, "chores/_assignment_row.html")
        self.assertContains(response, f'id="assignment-{assignment.id}"')

    def test_reassign_returns_assignment_row_partial(self):
        self.client.get("/")
        assignment = WeeklyAssignment.objects.get(chore=self.chore)
        response = self.client.post(
            f"/assignments/{assignment.id}/reassign/", {"member_id": self.bob.id}
        )
        self.assertTemplateUsed(response, "chores/_assignment_row.html")
        self.assertContains(response, f'id="assignment-{assignment.id}"')

    def test_unassigned_row_shows_disabled_placeholder_option(self):
        self.client.get("/")
        assignment = WeeklyAssignment.objects.get(chore=self.chore)
        assignment.assigned_member = None
        assignment.save()
        response = self.client.get("/")
        self.assertContains(response, '<option value="" disabled selected>')
