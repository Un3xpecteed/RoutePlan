# RoutesManagementService/project_config/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse  # Импортируем
from django.urls import include, path


# Простой Health Check Endpoint
def health_check(request):
    return JsonResponse({"status": "healthy"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("users/", include("apps.users.urls")),
    path("tasks/", include("apps.tasks.urls")),
    # path("", include("apps.routes.urls")), # Если это ваш корневой роут
    path("health/", health_check, name="health_check"),  # Новый эндпоинт
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
