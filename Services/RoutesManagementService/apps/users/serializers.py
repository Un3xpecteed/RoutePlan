from rest_framework import serializers

from apps.users.models import CustomUser


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser

        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "date_joined",
            "last_login",
        ]
        read_only_fields = ["id", "date_joined", "last_login", "is_active"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        label="Confirm password",
        style={"input_type": "password"},
    )

    class Meta:
        model = CustomUser
        fields = [
            "username",
            "email",
            "password",
            "password2",
            "first_name",
            "last_name",
            "role",
        ]
        extra_kwargs = {
            "first_name": {"required": False},
            "last_name": {"required": False},
            "role": {"required": False},
        }

    def validate_email(self, value):
        """
        Проверка, что email еще не занят.
        """
        if CustomUser.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def validate_username(self, value):
        """
        Проверка, что username еще не занят.
        """
        if CustomUser.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "A user with that username already exists."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")

        role = validated_data.pop("role", CustomUser.Roles.GUEST)

        user = CustomUser.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            role=role,
        )
        return user
