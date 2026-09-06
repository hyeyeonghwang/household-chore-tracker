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
