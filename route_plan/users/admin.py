from django.contrib import admin

# Register your models here.
from users.models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "email", "first_name", "last_name", "role")
    list_display_links = ("id", "username")
    search_fields = ("username", "email")
    list_filter = ("role",)
    ordering = ("username",)
