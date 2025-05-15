from django.contrib import admin

from app.models import Port


@admin.register(Port)
class PortAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "country", "latitude", "longitude", "timezone")
