from django.db import models


class VesselType(models.Model):
    name = models.CharField(
        max_length=100, unique=True, help_text="e.g., Cargo, Tanker, High-Speed Craft"
    )

    class Meta:
        verbose_name = "Vessel Type"
        verbose_name_plural = "Vessel Types"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Vessel(models.Model):
    name = models.CharField(
        max_length=150, help_text="User-friendly name or identifier for the vessel."
    )
    vessel_type = models.ForeignKey(
        VesselType,
        on_delete=models.PROTECT,
        help_text="The type of the vessel.",
    )
    average_speed_knots = models.FloatField(
        help_text="Average operational speed of this specific vessel in knots. Used for ETA calculations."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vessel"
        verbose_name_plural = "Vessels"
        ordering = ["name"]

    def __str__(self):
        return self.name
