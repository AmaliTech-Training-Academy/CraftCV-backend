from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["firstName", "lastName", "otherName", "password", "agreeToTerms"]

    def validate_agreeToTerms(self, value):
        if not value:
            raise serializers.ValidationError("You must agree to the terms to register")
        return value
