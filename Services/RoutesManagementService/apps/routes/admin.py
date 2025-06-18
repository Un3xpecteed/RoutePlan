from django.contrib import admin

from apps.routes.models import Route, RouteWaypoint

# Register your models here.
admin.site.register(Route)
admin.site.register(RouteWaypoint)
