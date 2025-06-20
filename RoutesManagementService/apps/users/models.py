from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        GUEST = "GUEST", ("Guest")
        CAPTAIN = "CAPTAIN", ("Captain")
        ADMIN = "ADMIN", ("Admin")

    role = models.CharField(
        "role",
        max_length=50,
        choices=Roles.choices,
        default=Roles.GUEST,
        help_text=("role of the user"),
    )

    def __str__(self):
        return self.username
