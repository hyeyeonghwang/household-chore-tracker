from django import forms

from .models import Chore, Household


class HouseholdForm(forms.ModelForm):
    class Meta:
        model = Household
        fields = ["name", "rotation_day"]


class ChoreForm(forms.ModelForm):
    class Meta:
        model = Chore
        fields = ["name", "description"]
