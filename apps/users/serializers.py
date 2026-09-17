from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    agree_to_terms = serializers.BooleanField(required=True)

    class Meta:
        model = User
        fields = ["email", "password", "agree_to_terms"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_agree_to_terms(self, value):
        if not value:
            raise serializers.ValidationError("You must agree to the terms to register")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    remember_me = serializers.BooleanField(default=False)


class TokenPayloadSerializer(serializers.Serializer):
    user = UserSerializer()
    access = serializers.CharField()
    refresh = serializers.CharField()
