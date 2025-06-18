from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Port(models.Model):
    name = models.CharField("name", max_length=150, unique=True)
    country = models.CharField("country", max_length=100)
    latitude = models.FloatField(
        "latitude",
        validators=[MinValueValidator(-90.0), MaxValueValidator(90.0)],
    )
    longitude = models.FloatField(
        "longitude",
        validators=[MinValueValidator(-180.0), MaxValueValidator(180.0)],
    )
    timezone = models.IntegerField(
        "timezone UTC",
        default=0,
        help_text="UTC+0 = 0, UTC+1 = 1, UTC-1 = -1 и т.д.",
        validators=[
            MinValueValidator(-12),
            MaxValueValidator(14),
        ],
    )

    class Meta:
        verbose_name = "Port"
        verbose_name_plural = "Ports"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.country})"


class Segment(models.Model):
    PortOfDeparture = models.ForeignKey(
        Port,
        verbose_name="port of departure",
        on_delete=models.PROTECT,
        related_name="departing_segments",
    )
    PortOfArrival = models.ForeignKey(
        Port,
        verbose_name="port of arrival",
        on_delete=models.PROTECT,
        related_name="arriving_segments",
    )
    distance = models.FloatField(
        "distance", default=0, help_text="distance in nautical miles"
    )
    average_speed = models.FloatField("average speed", default=0, blank=True)
    estimated_time = models.FloatField("estimated time", default=0, blank=True)

    class Meta:
        verbose_name = "Segment"
        verbose_name_plural = "Segments"
        ordering = ["PortOfDeparture__name", "PortOfArrival__name"]

    def __str__(self):
        departure_name = self.PortOfDeparture.name if self.PortOfDeparture else "N/A"
        arrival_name = self.PortOfArrival.name if self.PortOfArrival else "N/A"
        return f"Segment: {departure_name} -> {arrival_name} ({self.distance:.1f} nm)"

    def clean(self):
        super().clean()
        errors = {}
        if self.PortOfDeparture and self.PortOfArrival:
            if self.PortOfDeparture == self.PortOfArrival:
                msg = "Порт отправления не может совпадать с портом назначения."
                errors.setdefault("PortOfDeparture", []).append(
                    ValidationError(msg, code="ports_are_identical")
                )
                errors.setdefault("PortOfArrival", []).append(
                    ValidationError(msg, code="ports_are_identical")
                )

        if (
            self.PortOfDeparture
            and self.PortOfArrival
            and self.PortOfDeparture != self.PortOfArrival
        ):
            if self.distance is not None and self.distance <= 0:
                msg = "Расстояние между различными портами должно быть строго больше нуля."
                errors.setdefault("distance", []).append(
                    ValidationError(msg, code="non_positive_distance")
                )

        if errors:
            raise ValidationError(errors)
