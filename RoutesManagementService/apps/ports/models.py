from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Port(models.Model):
    name = models.CharField(
        "name", max_length=150, unique=True
    )  # Добавил unique=True, если имя порта должно быть уникальным
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
        ordering = ["name"]  # Сортировка по имени по умолчанию

    def __str__(self):
        return f"{self.name} ({self.country})"
        # Альтернатива, если страна не нужна для быстрого отображения:
        # return self.name


class Segment(models.Model):
    PortOfDeparture = models.ForeignKey(
        Port,
        verbose_name="port of departure",
        on_delete=models.PROTECT,  # PROTECT - хороший выбор, если нельзя удалять порты, на которые есть ссылки
        related_name="departing_segments",  # Более явное имя для обратной связи от Port
    )
    PortOfArrival = models.ForeignKey(
        Port,
        verbose_name="port of arrival",
        on_delete=models.PROTECT,
        related_name="arriving_segments",  # Более явное имя для обратной связи от Port
    )
    distance = models.FloatField(
        "distance", default=0, help_text="distance in nautical miles"
    )
    average_speed = models.FloatField(
        "average speed", default=0, blank=True
    )  # Сделал blank=True, если может быть не задано
    estimated_time = models.FloatField(
        "estimated time", default=0, blank=True
    )  # Сделал blank=True

    class Meta:
        verbose_name = "Segment"
        verbose_name_plural = "Segments"
        # Сортировка по именам связанных портов
        ordering = ["PortOfDeparture__name", "PortOfArrival__name"]
        # unique_together = ("PortOfDeparture", "PortOfArrival")

    def __str__(self):
        # Твой метод был хорош, немного его уточним для надежности
        departure_name = self.PortOfDeparture.name if self.PortOfDeparture else "N/A"
        arrival_name = self.PortOfArrival.name if self.PortOfArrival else "N/A"
        return f"Segment: {departure_name} -> {arrival_name} ({self.distance:.1f} nm)"  # Оставим 1 знак после запятой для дистанции

    def clean(self):  # Твой метод clean остается
        super().clean()
        errors = {}
        if self.PortOfDeparture and self.PortOfArrival:
            if self.PortOfDeparture == self.PortOfArrival:
                msg = "Порт отправления не может совпадать с портом назначения."
                # Добавляем ошибки к обоим полям, если они идентичны
                errors.setdefault("PortOfDeparture", []).append(
                    ValidationError(msg, code="ports_are_identical")
                )
                errors.setdefault("PortOfArrival", []).append(
                    ValidationError(msg, code="ports_are_identical")
                )

        # Проверка на отрицательное расстояние, только если порты разные
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

        # Если это новый объект и расстояние 0, а порты одинаковые - это не ошибка расстояния
        # Эта логика уже покрыта первой проверкой.
        # Дополнительная проверка для нулевого расстояния при одинаковых портах не нужна,
        # так как первая ошибка (PortOfDeparture == PortOfArrival) уже будет сгенерирована.

        if errors:
            raise ValidationError(errors)
