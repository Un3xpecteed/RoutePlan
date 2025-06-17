from django.contrib import admin
from django.http import HttpResponse  # Импортируем HttpResponse для health check
from django.urls import include, path


# Функция-представление для health check
def health_check_view(request):
    return HttpResponse("OK", status=200)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    # Эндпоинт для health check
    path("health/", health_check_view),
    # --- ДОБАВЬТЕ ЭТУ СТРОКУ ---
    path("routes-task/", include("apps.routes.urls")),
    # --- КОНЕЦ ДОБАВЛЕНИЯ ---
]
