from django.db import models


# Create your models here.
class Port(models.Model):
    class Meta:
        verbose_name = "Порт"
        verbose_name_plural = "Порты"

    name = models.CharField("Название порта", max_length=25)
    country = models.CharField("Страна", max_length=25)
    latitude = models.CharField("Широта", max_length=25)
    longitude = models.CharField("Долгота", max_length=25)
    timezone = models.IntegerField("Часовой пояс", default=0)

    def __str__(self):
        return self.name
