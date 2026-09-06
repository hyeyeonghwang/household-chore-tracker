from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render

from .decorators import get_current_membership
from .forms import HouseholdForm
from .models import Membership


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("create_household")
    else:
        form = UserCreationForm()
    return render(request, "chores/signup.html", {"form": form})


@login_required
def create_household(request):
    if get_current_membership(request) is not None:
        return redirect("/")
    if request.method == "POST":
        form = HouseholdForm(request.POST)
        if form.is_valid():
            household = form.save()
            Membership.objects.create_next(household, request.user)
            return redirect("/")
    else:
        form = HouseholdForm()
    return render(request, "chores/create_household.html", {"form": form})
