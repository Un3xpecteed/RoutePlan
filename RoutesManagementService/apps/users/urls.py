# RoutesManagementService/apps/users/urls.py
from django.urls import path

from . import views  # Импортируем наше представление

app_name = "users"  # Имя приложения для reverse lookup

urlpatterns = [
    path("register/", views.register, name="register"),
    # Здесь можно добавить другие URL для управления пользователями, если они понадобятся
]
