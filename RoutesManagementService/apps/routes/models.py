from django.conf import settings
from django.db import models

from apps.ports.models import Port

# Create your models here.


class Route(models.Model):
    class Meta:
        verbose_name = "Route"
        verbose_name_plural = "Routes"

    name = models.CharField("name", max_length=150)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="created by",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("created at", auto_now_add=True)
    is_public = models.BooleanField("public", default=False)

    def __str__(self):
        return self.name


class RouteWaypoint(models.Model):
    class Meta:
        verbose_name = "waypoint"
        verbose_name_plural = "waypoints"
        ordering = ["route", "order"]
        unique_together = ("route", "order")

    route = models.ForeignKey(
        Route,
        verbose_name="waypoints",
        on_delete=models.CASCADE,
        related_name="waypoints",
    )
    port = models.ForeignKey(
        Port,
        verbose_name="port",
        on_delete=models.PROTECT,
        related_name="route_waypoints",
    )
    order = models.IntegerField("order", default=0)
    ETA = models.DateTimeField("ETA", null=True, blank=True)
    ETD = models.DateTimeField("ETD", null=True, blank=True)

    def __str__(self):
        return f"{self.route.name} - {self.port.name}"
