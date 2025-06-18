from django.contrib import admin

from apps.vessels.models import Vessel, VesselType

# Register your models here.
admin.site.register(Vessel)
admin.site.register(VesselType)
