from django import forms

from apps.ports.models import Port


class RouteCalculationForm(forms.Form):
    start_port = forms.ModelChoiceField(
        queryset=Port.objects.order_by("name"),
        label="Порт отправления",
        empty_label="Выберите порт",
    )
    end_port = forms.ModelChoiceField(
        queryset=Port.objects.order_by("name"),
        label="Порт назначения",
        empty_label="Выберите порт",
    )

    def clean(self):
        cleaned_data = super().clean()
        start_port = cleaned_data.get("start_port")
        end_port = cleaned_data.get("end_port")

        if start_port and end_port:
            if start_port == end_port:
                raise forms.ValidationError()
        return cleaned_data
