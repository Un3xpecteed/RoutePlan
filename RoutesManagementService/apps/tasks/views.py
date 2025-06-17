import logging

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse  # Убедись, что reverse импортирован
from django.views import View

# Импортируем модели и продюсер из других приложений
from apps.ports.models import Port
from apps.tasks.kafka_producer import (
    send_calculation_request,  # Из приложения 'routes'
)
from apps.tasks.models import (
    CalculationTask,  # Модель CalculationTask из приложения 'routes'
)

# Импортируем форму из текущего приложения 'tasks'
from .forms import (
    RouteCalculationForm,  # Предполагаем, что forms.py в apps/tasks/forms.py
)

# TODO: Когда будет Redis, раскомментируй и убедись в правильности пути
# from apps.routes.redis_client import get_task_status_from_redis, clear_task_status_from_redis, redis_client

logger = logging.getLogger(__name__)


class CreateCalculationTaskView(View):
    # Путь к шаблону. Например, 'tasks/create_task_form.html'
    # Убедись, что этот шаблон существует в apps/tasks/templates/tasks/
    # или в глобальной директории шаблонов templates/tasks/
    template_name = "tasks/create_task_form.html"

    def get(self, request, *args, **kwargs):
        form = RouteCalculationForm()
        recent_tasks = CalculationTask.objects.order_by("-created_at")[:5]
        context = {"form": form, "recent_tasks": recent_tasks}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = RouteCalculationForm(request.POST)
        if form.is_valid():
            start_port = form.cleaned_data["start_port"]
            end_port = form.cleaned_data["end_port"]

            task = CalculationTask.objects.create(
                start_port=start_port,
                end_port=end_port,
                status=CalculationTask.StatusChoices.PENDING,  # Используем Model.InnerEnum.VALUE
            )

            kafka_send_successful = send_calculation_request(
                task_id=str(task.task_id),
                start_port_id=start_port.id,
                end_port_id=end_port.id,
            )

            if kafka_send_successful:
                messages.success(
                    request,
                    f"Задача расчета маршрута {task.task_id} успешно отправлена в обработку.",
                )
                # URL 'task_status' находится в приложении 'routes' (согласно твоему apps/routes/urls.py)
                return redirect(
                    reverse("routes:task_status", kwargs={"task_id": task.task_id})
                )
            else:
                task.status = (
                    CalculationTask.StatusChoices.FAILED
                )  # Используем Model.InnerEnum.VALUE
                task.error_message = (
                    "Ошибка: Не удалось отправить задачу в очередь обработки Kafka."
                )
                task.save()
                messages.error(
                    request,
                    "Произошла ошибка при отправке задачи в обработку. Пожалуйста, попробуйте позже.",
                )

        recent_tasks = CalculationTask.objects.order_by("-created_at")[:5]
        context = {"form": form, "recent_tasks": recent_tasks}
        return render(request, self.template_name, context)


class CalculationTaskStatusView(View):
    template_name = "tasks/task_status.html"  # Шаблон в apps/tasks/templates/tasks/

    def get(self, request, task_id, *args, **kwargs):
        task_db_obj = get_object_or_404(CalculationTask, task_id=task_id)

        final_task_data_for_template = {}

        # TODO: Логика для Redis
        # source_data = "db"
        # redis_status_data = get_task_status_from_redis(str(task_id))
        # if redis_status_data and redis_status_data.get('status_code') not in [
        #     CalculationTask.StatusChoices.COMPLETED, CalculationTask.StatusChoices.FAILED
        # ]:
        #     final_task_data_for_template = { ... из Redis ... , "source": "redis"}
        #     source_data = "redis"
        #     if request.headers.get("x-requested-with") == "XMLHttpRequest":
        #         return JsonResponse(final_task_data_for_template)

        path_ports_details = []
        if (
            task_db_obj.status == CalculationTask.StatusChoices.COMPLETED
            and task_db_obj.result_path
        ):
            try:
                port_ids = task_db_obj.result_path
                if isinstance(port_ids, list):
                    ports_in_path_map = Port.objects.filter(id__in=port_ids).in_bulk()
                    for port_id_in_path in port_ids:
                        port_obj = ports_in_path_map.get(port_id_in_path)
                        if port_obj:
                            path_ports_details.append(
                                {
                                    "id": port_obj.id,
                                    "name": port_obj.name,
                                    "latitude": port_obj.latitude,
                                    "longitude": port_obj.longitude,
                                }
                            )
                        else:
                            path_ports_details.append(
                                {
                                    "id": port_id_in_path,
                                    "name": f"Порт ID {port_id_in_path} не найден",
                                }
                            )
                else:
                    logger.warning(
                        f"result_path для задачи {task_db_obj.task_id} не является списком: {task_db_obj.result_path}"
                    )
            except Exception as e:
                logger.error(
                    f"Ошибка при обработке result_path для задачи {task_db_obj.task_id} из БД: {e}",
                    exc_info=True,
                )

        db_sourced_data = {
            "task_id": str(task_db_obj.task_id),
            "status_code": task_db_obj.status,
            "status_display": task_db_obj.get_status_display(),  # Метод модели Django
            "start_port_name": task_db_obj.start_port.name,
            "end_port_name": task_db_obj.end_port.name,
            "result_path_details": path_ports_details,
            "result_distance": task_db_obj.result_distance,
            "error_message": task_db_obj.error_message,
            "created_at": task_db_obj.created_at.isoformat()
            if task_db_obj.created_at
            else None,
            "updated_at": task_db_obj.updated_at.isoformat()
            if task_db_obj.updated_at
            else None,
            "source": "db",
        }

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            # TODO: Если задача COMPLETED/FAILED, можно очистить из Redis
            # if task_db_obj.status in [CalculationTask.StatusChoices.COMPLETED, CalculationTask.StatusChoices.FAILED]:
            #     if redis_client: clear_task_status_from_redis(str(task_db_obj.task_id))
            return JsonResponse(db_sourced_data)

        if not final_task_data_for_template:
            final_task_data_for_template = db_sourced_data

        context = {
            "task_db_obj": task_db_obj,
            "task_data": final_task_data_for_template,
        }
        return render(request, self.template_name, context)
