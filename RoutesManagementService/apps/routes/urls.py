# RoutesManagementService/apps/routes/urls.py
from django.urls import path

# Изменяем импорт, чтобы он указывал на views из приложения 'tasks'
from apps.tasks.views import CalculationTaskStatusView, CreateCalculationTaskView

# Альтернативный вариант, если 'tasks' и 'routes' на одном уровне в 'apps'
# from ..tasks.views import CalculationTaskStatusView, CreateCalculationTaskView

app_name = "routes"

urlpatterns = [
    path(
        "calculate/", CreateCalculationTaskView.as_view(), name="calculate_task_create"
    ),
    path(
        "task/<uuid:task_id>/status/",
        CalculationTaskStatusView.as_view(),
        name="task_status",
    ),
]
