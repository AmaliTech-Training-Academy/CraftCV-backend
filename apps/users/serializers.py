from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "firstName",
            "lastName",
            "otherName",
            "createdAt",
        ]
        read_only_fields = ["id", "createdAt"]


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["firstName", "lastName", "otherName", "password", "agreeToTerms"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_agreeToTerms(self, value):
        if not value:
            raise serializers.ValidationError("You must agree to the terms to register")
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
