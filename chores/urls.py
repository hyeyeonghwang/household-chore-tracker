from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", views.signup, name="signup"),
    path("create-household/", views.create_household, name="create_household"),
    path("", views.this_week, name="this_week"),
    path("assignments/<int:assignment_id>/mark-done/", views.mark_done, name="mark_done"),
    path("assignments/<int:assignment_id>/reassign/", views.reassign, name="reassign"),
    path("chores/", views.chores_list, name="chores_list"),
    path("chores/<int:chore_id>/edit/", views.chore_edit, name="chore_edit"),
    path("chores/<int:chore_id>/delete/", views.chore_delete, name="chore_delete"),
    path("members/", views.members_list, name="members_list"),
    path("members/<int:membership_id>/remove/", views.member_remove, name="member_remove"),
]
