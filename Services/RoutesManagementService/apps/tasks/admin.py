from django.contrib import admin

from .models import CalculationTask


@admin.register(CalculationTask)
class CalculationTaskAdmin(admin.ModelAdmin):
    list_display = (
        "task_id",
        "start_port",
        "end_port",
        "status",
        "created_at",
        "updated_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("task_id", "start_port__name", "end_port__name")
    readonly_fields = (
        "task_id",
        "created_at",
        "updated_at",
        "result_path",
        "result_distance",
        "error_message",
    )
