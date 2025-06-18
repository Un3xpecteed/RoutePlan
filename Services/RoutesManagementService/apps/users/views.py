# RoutesManagementService/apps/users/views.py
from django.contrib.auth import login
from django.shortcuts import redirect, render

from .forms import CustomUserCreationForm  # Наша новая форма


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Автоматический логин после регистрации
            return redirect("tasks:calculate_task_create")  # Перенаправление
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})
