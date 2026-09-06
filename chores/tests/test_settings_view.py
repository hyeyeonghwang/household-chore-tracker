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

    def test_invalid_rotation_day_is_rejected(self):
        response = self.client.post("/settings/", {"name": "Jones House", "rotation_day": 99})
        self.household.refresh_from_db()
        self.assertNotEqual(self.household.rotation_day, 99)
