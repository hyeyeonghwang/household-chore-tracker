from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .decorators import get_current_membership, household_required
from .forms import ChoreForm, HouseholdForm
from .models import Chore, Membership, WeeklyAssignment
from .rotation import ensure_current_week


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


@login_required
@household_required
def this_week(request):
    household = request.membership.household
    week_start = ensure_current_week(household)
    assignments = (
        WeeklyAssignment.objects.filter(chore__household=household, week_start_date=week_start)
        .select_related("chore", "assigned_member__user")
        .order_by("chore__name")
    )
    return render(
        request,
        "chores/this_week.html",
        {"assignments": assignments},
    )


@login_required
@household_required
@require_POST
def mark_done(request, assignment_id):
    household = request.membership.household
    assignment = get_object_or_404(
        WeeklyAssignment, id=assignment_id, chore__household=household
    )
    assignment.status = WeeklyAssignment.DONE
    assignment.save(update_fields=["status"])
    return render(request, "chores/_assignment_row.html", {"assignment": assignment})


@login_required
@household_required
@require_POST
def reassign(request, assignment_id):
    household = request.membership.household
    assignment = get_object_or_404(
        WeeklyAssignment, id=assignment_id, chore__household=household
    )
    member = get_object_or_404(
        Membership, id=request.POST.get("member_id"), household=household, is_active=True
    )
    assignment.assigned_member = member
    assignment.is_manual_override = True
    assignment.save(update_fields=["assigned_member", "is_manual_override"])
    return render(request, "chores/_assignment_row.html", {"assignment": assignment})


@login_required
@household_required
def chores_list(request):
    household = request.membership.household
    if request.method == "POST":
        form = ChoreForm(request.POST)
        if form.is_valid():
            Chore.objects.create_with_offset(
                household,
                form.cleaned_data["name"],
                description=form.cleaned_data["description"],
            )
            return redirect("chores_list")
    else:
        form = ChoreForm()
    chores = household.chores.all().order_by("name")
    return render(request, "chores/chores_list.html", {"chores": chores, "form": form})


@login_required
@household_required
def chore_edit(request, chore_id):
    household = request.membership.household
    chore = get_object_or_404(Chore, id=chore_id, household=household)
    if request.method == "POST":
        form = ChoreForm(request.POST, instance=chore)
        if form.is_valid():
            form.save()
            return redirect("chores_list")
    else:
        form = ChoreForm(instance=chore)
    return render(request, "chores/chore_form.html", {"form": form, "chore": chore})


@login_required
@household_required
@require_POST
def chore_delete(request, chore_id):
    household = request.membership.household
    chore = get_object_or_404(Chore, id=chore_id, household=household)
    chore.delete()
    return redirect("chores_list")
