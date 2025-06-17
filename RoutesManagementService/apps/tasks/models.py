import uuid

from django.db import models

from apps.ports.models import Port


class CalculationTask(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "PENDING"
        PROCESSING = "PROCESSING"
        COMPLETED = "COMPLETED"
        FAILED = "FAILED"

    task_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True
    )

    start_port = models.ForeignKey(
        Port,
        on_delete=models.CASCADE,
        related_name="calculation_tasks_as_start",
    )
    end_port = models.ForeignKey(
        Port,
        on_delete=models.CASCADE,
        related_name="calculation_tasks_as_end",
    )
    status = models.CharField(
        max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Результаты расчета
    result_path = models.JSONField(
        null=True, blank=True, help_text="Список ID портов в маршруте"
    )
    result_distance = models.FloatField(
        null=True, blank=True, help_text="Общая дистанция в морских милях"
    )
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Task {self.task_id} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Задача расчета маршрута"
        verbose_name_plural = "Задачи расчета маршрутов"
        ordering = ["-created_at"]
