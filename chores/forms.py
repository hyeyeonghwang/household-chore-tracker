from django import forms

from .models import Household


class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ["name", "rotation_day"]
