from django.urls import path
from django.views.generic import TemplateView

app_name = "ports"


urlpatterns = [
    path("", TemplateView.as_view(template_name="ports/index.html"), name="index"),
]
