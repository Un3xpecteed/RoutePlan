from rest_framework import serializers

from apps.ports.models import Port, Segment


class PortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Port
        fields = "__all__"


class SegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Segment
        fields = "__all__"
