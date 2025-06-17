# RoutesManagementService/apps/tasks/urls.py
from django.urls import path

from .views import CalculationTaskStatusView, CreateCalculationTaskView

app_name = "tasks"  # Имя приложения для reverse lookup

urlpatterns = [
    path("create/", CreateCalculationTaskView.as_view(), name="calculate_task_create"),
    path("<uuid:task_id>/", CalculationTaskStatusView.as_view(), name="task_status"),
]
