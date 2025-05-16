from django.contrib import admin

from app.models import Port, Route, RouteWaypoint, Segment


@admin.register(Port)
class PortAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "country", "latitude", "longitude", "timezone")
    list_display_links = ("id", "name")
    search_fields = ("name", "country")
    list_filter = ("country",)
    ordering = ("name",)


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_by", "created_at", "is_public")
    list_display_links = ("id", "name")
    search_fields = ("name", "created_by")
    list_filter = ("is_public", "created_at")
    ordering = ("-created_at",)


@admin.register(RouteWaypoint)
class RouteWaypointAdmin(admin.ModelAdmin):
    list_display = ("id", "route", "port", "order")
    list_display_links = ("id", "route")
    search_fields = ("route__name", "port__name")
    list_filter = ("route",)
    ordering = ("route", "order")


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "PortOfDeparture",
        "PortOfArrival",
        "distance",
        "average_speed",
        "estimated_time",
    )
    list_display_links = ("id", "PortOfDeparture", "PortOfArrival")
    search_fields = ("PortOfDeparture__name", "PortOfArrival__name")
    list_filter = ("PortOfDeparture", "PortOfArrival")
    ordering = ("PortOfDeparture", "PortOfArrival")
