from rest_framework import serializers

from apps.vessels.models import Vessel, VesselType


class VesselSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vessel
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]


class VesselTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VesselType
        fields = "__all__"
