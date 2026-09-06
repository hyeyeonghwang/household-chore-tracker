from django.contrib import admin

from .models import Chore, Household, Membership, WeeklyAssignment

admin.site.register(Household)
admin.site.register(Membership)
admin.site.register(Chore)
admin.site.register(WeeklyAssignment)
