from functools import wraps

from django.shortcuts import redirect

from .models import Membership


def get_current_membership(request):
    if not request.user.is_authenticated:
        return None
    return Membership.objects.filter(user=request.user, is_active=True).first()


def household_required(view_func):
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        membership = get_current_membership(request)
        if membership is None:
            return redirect("create_household")
        request.membership = membership
        return view_func(request, *args, **kwargs)

    return wrapped
