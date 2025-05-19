from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


# Create your models here.
class Port(models.Model):
    class Meta:
        verbose_name = "Порт"
        verbose_name_plural = "Порты"

    name = models.CharField("Название порта", max_length=150)
    country = models.CharField("Страна", max_length=100)
    latitude = models.FloatField(
        "Широта",
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
    )
    longitude = models.FloatField(
        "Долгота",
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
    )
    timezone = models.IntegerField(
        "Часовой пояс (Смещение от UTC)",
        default=0,
        help_text="UTC+0 = 0, UTC+1 = 1, UTC-1 = -1 и т.д.",
        validators=[
            MinValueValidator(-12),
            MaxValueValidator(14),
        ],
    )

    def __str__(self):
        return self.name


class Route(models.Model):
    class Meta:
        verbose_name = "Маршрут"
        verbose_name_plural = "Маршруты"

    name = models.CharField("Название маршрута", max_length=150)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Создатель",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    is_public = models.BooleanField("Публичный", default=False)

    def __str__(self):
        return self.name


class RouteWaypoint(models.Model):
    class Meta:
        verbose_name = "Маршрутная точка"
        verbose_name_plural = "Маршрутные точки"
        ordering = ["route", "order"]
        unique_together = ("route", "order")

    route = models.ForeignKey(
        Route,
        verbose_name="Маршрут",
        on_delete=models.CASCADE,
        related_name="waypoints",
    )
    port = models.ForeignKey(
        Port,
        verbose_name="Порт",
        on_delete=models.PROTECT,
        related_name="route_waypoints",
    )
    order = models.IntegerField("Порядок", default=0)
    ETA = models.DateTimeField("ETA", null=True, blank=True)
    ETD = models.DateTimeField("ETD", null=True, blank=True)

    def __str__(self):
        return f"{self.route.name} - {self.port.name}"


class Segment(models.Model):
    class Meta:
        verbose_name = "Граф"
        verbose_name_plural = "Граф портов"
        ordering = ["PortOfDeparture", "PortOfArrival"]
        unique_together = ("PortOfDeparture", "PortOfArrival")

    PortOfDeparture = models.ForeignKey(
        Port,
        verbose_name="Порт отправления",
        on_delete=models.PROTECT,
        related_name="port_of_departure",
    )

    PortOfArrival = models.ForeignKey(
        Port,
        verbose_name="Порт назначения",
        on_delete=models.PROTECT,
        related_name="port_of_arrival",
    )
    distance = models.FloatField(
        "Расстояние", default=0, help_text="Расстояние в милях"
    )
    average_speed = models.FloatField("Средняя скорость", default=0)
    estimated_time = models.FloatField("Расчетное время", default=0)

    def clean(self):
        super().clean()

        errors = {}

        if self.PortOfDeparture and self.PortOfArrival:
            if self.PortOfDeparture == self.PortOfArrival:
                msg = "Порт отправления не может совпадать с портом назначения."
                if "PortOfDeparture" not in errors:
                    errors["PortOfDeparture"] = []
                errors["PortOfDeparture"].append(
                    ValidationError(msg, code="ports_are_identical")
                )
                if "PortOfArrival" not in errors:
                    errors["PortOfArrival"] = []
                errors["PortOfArrival"].append(
                    ValidationError(msg, code="ports_are_identical")
                )

        if (
            self.PortOfDeparture
            and self.PortOfArrival
            and self.PortOfDeparture_id != self.PortOfArrival_id
        ):
            if self.distance is not None and self.distance <= 0:
                # Просто используем обычную строку
                msg = "Расстояние между различными портами должно быть строго больше нуля."
                if "distance" not in errors:
                    errors["distance"] = []
                errors["distance"].append(
                    ValidationError(msg, code="non_positive_distance")
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.PortOfDeparture.name} - {self.PortOfArrival.name}"
