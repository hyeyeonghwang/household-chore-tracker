from django.contrib.auth import get_user_model
from django.test import TestCase

from chores.models import Chore, Household, Membership, WeeklyAssignment

User = get_user_model()


class LoginRequiredTests(TestCase):
    def setUp(self):
        self.household = Household.objects.create(name="Smith House", rotation_day=0)
        user = User.objects.create_user(username="alice", password="pw")
        self.membership = Membership.objects.create_next(self.household, user)
        self.chore = Chore.objects.create_with_offset(self.household, "Trash")
        self.assignment = WeeklyAssignment.objects.create(
            chore=self.chore, week_start_date="2026-01-05", status=WeeklyAssignment.PENDING
        )

    def test_anonymous_user_redirected_to_login(self):
        urls = [
            "/",
            f"/assignments/{self.assignment.id}/mark-done/",
            f"/assignments/{self.assignment.id}/reassign/",
            "/chores/",
            f"/chores/{self.chore.id}/edit/",
            f"/chores/{self.chore.id}/delete/",
            "/members/",
            f"/members/{self.membership.id}/remove/",
            "/settings/",
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"{url} did not redirect")
            self.assertTrue(
                response["Location"].startswith("/login/"),
                f"{url} redirected to {response['Location']} instead of /login/",
            )
