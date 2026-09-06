from django.conf import settings
from django.db import models
from django.utils import timezone


class Household(models.Model):
    name = models.CharField(max_length=100)
    rotation_day = models.IntegerField(default=0)  # 0=Monday ... 6=Sunday

    def __str__(self):
        return self.name


class MembershipManager(models.Manager):
    def create_next(self, household, user):
        last = (
            self.filter(household=household)
            .order_by("-rotation_order")
            .first()
        )
        next_order = 0 if last is None else last.rotation_order + 1
        return self.create(household=household, user=user, rotation_order=next_order)


class Membership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="memberships")
    rotation_order = models.IntegerField()
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)

    objects = MembershipManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["household", "rotation_order"],
                name="unique_rotation_order_per_household",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} @ {self.household.name}"

    def deactivate(self):
        self.is_active = False
        self.left_at = timezone.now()
        self.save(update_fields=["is_active", "left_at"])
