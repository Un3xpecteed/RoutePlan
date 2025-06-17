from django.contrib import admin

from apps.ports.models import Port, Segment

# Register your models here.

admin.site.register(Port)


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "PortOfDeparture",
        "PortOfArrival",
        "distance",
        "average_speed",
        "estimated_time",
    ]
