from django.conf import settings
from django.db import models
from django.utils import timezone


class Household(models.Model):
    ROTATION_DAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]
    name = models.CharField(max_length=100)
    rotation_day = models.IntegerField(default=0, choices=ROTATION_DAYS)

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


class ChoreManager(models.Manager):
    def create_with_offset(self, household, name, description=""):
        active_orders = list(
            household.memberships.filter(is_active=True)
            .order_by("rotation_order")
            .values_list("rotation_order", flat=True)
        )
        existing_count = self.filter(household=household).count()
        if active_orders:
            n = len(active_orders)
            offset_index = existing_count % n
            seed = active_orders[-1] if offset_index == 0 else active_orders[offset_index - 1]
        else:
            seed = -1
        return self.create(
            household=household,
            name=name,
            description=description,
            last_rotation_order=seed,
        )


class Chore(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="chores")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_rotation_order = models.IntegerField()

    objects = ChoreManager()

    def __str__(self):
        return self.name


class WeeklyAssignment(models.Model):
    PENDING = "pending"
    DONE = "done"
    STATUS_CHOICES = [(PENDING, "Pending"), (DONE, "Done")]

    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name="assignments")
    week_start_date = models.DateField()
    assigned_member = models.ForeignKey(
        Membership, on_delete=models.SET_NULL, null=True, blank=True, related_name="assignments"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    is_manual_override = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["chore", "week_start_date"],
                name="unique_assignment_per_chore_per_week",
            ),
        ]

    def __str__(self):
        return f"{self.chore.name} - {self.week_start_date}"
