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
    vessel_speed_knots = forms.FloatField(
        label="Скорость судна (узлы)",
        required=False,
        min_value=1.0,
        help_text="Оставьте пустым для расчета только расстояния. Для расчета времени введите скорость (только для Капитанов).",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_port"].widget.attrs.update({"class": "form-select"})
        self.fields["end_port"].widget.attrs.update({"class": "form-select"})
        self.fields["vessel_speed_knots"].widget.attrs.update({"class": "form-control"})

    def clean(self):
        cleaned_data = super().clean()
        start_port = cleaned_data.get("start_port")
        end_port = cleaned_data.get("end_port")
        vessel_speed_knots = cleaned_data.get("vessel_speed_knots")

        if start_port and end_port:
            if start_port == end_port:
                self.add_error(
                    "end_port", "Порт отправления и порт назначения не могут совпадать."
                )

        if vessel_speed_knots is not None and vessel_speed_knots <= 0:
            self.add_error(
                "vessel_speed_knots", "Скорость должна быть положительным числом."
            )

        return cleaned_data
