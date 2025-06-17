# RoutesManagementService/apps/tasks/models.py
import uuid

from django.db import models

from apps.ports.models import Port


class CalculationTask(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", ("В ожидании")
        PROCESSING = "PROCESSING", ("В обработке")
        COMPLETED = "COMPLETED", ("Завершено")
        FAILED = "FAILED", ("Ошибка")

    task_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )

    start_port = models.ForeignKey(
        Port,
        on_delete=models.CASCADE,
        related_name="calculation_tasks_as_start",
        verbose_name="Порт отправления",  # Добавил verbose_name
    )
    end_port = models.ForeignKey(
        Port,
        on_delete=models.CASCADE,
        related_name="calculation_tasks_as_end",
        verbose_name="Порт назначения",  # Добавил verbose_name
    )
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Дата создания"
    )  # Добавил verbose_name
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Дата обновления"
    )  # Добавил verbose_name

    # Новые поля для расчета времени
    vessel_speed_knots = models.FloatField(
        null=True,
        blank=True,
        help_text="Скорость судна в узлах (морских милях в час)",
        verbose_name="Скорость судна",  # Добавил verbose_name
    )
    # Результаты расчета
    result_path = models.JSONField(
        null=True, blank=True, help_text="Список ID портов в маршруте"
    )
    result_distance = models.FloatField(
        null=True, blank=True, help_text="Общая дистанция в морских милях"
    )
    result_waypoints_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Детальные данные по портам маршрута с ETA/ETD",
        verbose_name="Детали маршрута (ETA/ETD)",
    )
    error_message = models.TextField(
        blank=True, null=True, verbose_name="Сообщение об ошибке"
    )  # Добавил verbose_name

    def __str__(self):
        speed_info = (
            f" @ {self.vessel_speed_knots} kts" if self.vessel_speed_knots else ""
        )
        return f"Задача {self.task_id} ({self.get_status_display()}){speed_info}"

    class Meta:
        verbose_name = "Задача расчета маршрута"
        verbose_name_plural = "Задачи расчета маршрутов"
        ordering = ["-created_at"]
