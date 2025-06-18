from rest_framework import serializers

from apps.routes.models import Route, RouteWaypoint


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = "__all__"
        read_only_fields = ["port"]


class RouteWaypointSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteWaypoint
        fields = "__all__"
        read_only_fields = ["created_at", "waypoints"]
