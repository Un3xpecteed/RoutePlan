from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Roles(models.TextChoices):
        GUEST = "GUEST", ("Гость")
        CAPTAIN = "CAPTAIN", ("Капитан")
        ADMIN = "ADMIN", ("Админ")

    role = models.CharField(
        "Роль",
        max_length=50,
        choices=Roles.choices,
        default=Roles.GUEST,
        help_text=("Роль пользователя в системе"),
    )

    def __str__(self):
        return self.username
