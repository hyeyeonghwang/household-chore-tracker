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
