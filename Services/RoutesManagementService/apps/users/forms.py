# RoutesManagementService/apps/users/forms.py
from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        # Поля, которые пользователь будет вводить при регистрации:
        # role не включаем, так как оно будет по умолчанию GUEST
        fields = UserCreationForm.Meta.fields + ("email",)  # Добавим email

    # Можно добавить дополнительную валидацию, если нужно
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким Email уже существует.")
        return email


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = UserChangeForm.Meta.fields
