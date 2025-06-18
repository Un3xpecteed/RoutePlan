import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from apps.ports.models import Port
from apps.tasks.kafka_producer import send_calculation_request
from apps.tasks.models import CalculationTask
from apps.users.models import CustomUser

from .forms import RouteCalculationForm

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class CreateCalculationTaskView(View):
    template_name = "tasks/create_task_form.html"

    def get(self, request, *args, **kwargs):
        form = RouteCalculationForm()
        recent_tasks = CalculationTask.objects.order_by("-created_at")[:5]
        context = {
            "form": form,
            "recent_tasks": recent_tasks,
            "is_captain": request.user.is_authenticated
            and request.user.role == CustomUser.Roles.CAPTAIN,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = RouteCalculationForm(request.POST)
        if form.is_valid():
            start_port = form.cleaned_data["start_port"]
            end_port = form.cleaned_data["end_port"]
            vessel_speed_knots = form.cleaned_data.get("vessel_speed_knots")

            if vessel_speed_knots is not None:
                if not (
                    request.user.is_authenticated
                    and request.user.role == CustomUser.Roles.CAPTAIN
                ):
                    messages.error(
                        request,
                        "Только Капитан может указывать скорость судна для расчета времени.",
                    )
                    vessel_speed_knots = None
                elif vessel_speed_knots <= 0:
                    messages.error(
                        request, "Скорость судна должна быть положительным числом."
                    )
                    vessel_speed_knots = None

            task = CalculationTask.objects.create(
                start_port=start_port,
                end_port=end_port,
                vessel_speed_knots=vessel_speed_knots,
                status=CalculationTask.StatusChoices.PENDING,
            )

            kafka_send_successful = send_calculation_request(
                task_id=str(task.task_id),
                start_port_id=start_port.id,
                end_port_id=end_port.id,
                vessel_speed_knots=vessel_speed_knots,
            )

            if kafka_send_successful:
                messages.success(
                    request,
                    f"Задача расчета маршрута {task.task_id} успешно отправлена в обработку.",
                )
                return redirect(
                    reverse("tasks:task_status", kwargs={"task_id": task.task_id})
                )
            else:
                task.status = CalculationTask.StatusChoices.FAILED
                task.error_message = (
                    "Ошибка: Не удалось отправить задачу в очередь обработки Kafka."
                )
                task.save()
                messages.error(
                    request,
                    "Произошла ошибка при отправке задачи в обработку. Пожалуйста, попробуйте позже.",
                )

        recent_tasks = CalculationTask.objects.order_by("-created_at")[:5]
        context = {
            "form": form,
            "recent_tasks": recent_tasks,
            "is_captain": request.user.is_authenticated
            and request.user.role == CustomUser.Roles.CAPTAIN,
        }
        return render(request, self.template_name, context)


@method_decorator(login_required, name="dispatch")
class CalculationTaskStatusView(View):
    template_name = "tasks/task_status.html"

    def get(self, request, task_id, *args, **kwargs):
        task_db_obj = get_object_or_404(CalculationTask, task_id=task_id)

        logger.info(
            f"Task {task_id} result_waypoints_data from DB: {task_db_obj.result_waypoints_data}"
        )

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
                                    "latitude": None,
                                    "longitude": None,
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
            "status_display": task_db_obj.get_status_display(),
            "start_port_name": task_db_obj.start_port.name,
            "end_port_name": task_db_obj.end_port.name,
            "vessel_speed_knots": task_db_obj.vessel_speed_knots,
            "result_path_details": path_ports_details,
            "result_distance": task_db_obj.result_distance,
            "result_waypoints_data": task_db_obj.result_waypoints_data,
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
            return JsonResponse(db_sourced_data)

        context = {
            "task_db_obj": task_db_obj,
            "task_data": db_sourced_data,
        }
        return render(request, self.template_name, context)
