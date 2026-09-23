from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
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
    email = serializers.EmailField(
        write_only=True,
        error_messages={
            "blank": "Email field cannot be empty.",
            "required": "Email is required.",
        },
    )
    password = serializers.CharField(
        write_only=True,
        error_messages={
            "blank": "Password field cannot be empty.",
            "required": "Password is required.",
        },
    )
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


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={
            "blank": "Email cannot be empty.",
            "required": "Email is required.",
        }
    )


class VerifyCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={
            "blank": "Email cannot be empty.",
            "required": "Email is required.",
        }
    )
    code = serializers.CharField(
        min_length=6,
        max_length=6,
        error_messages={
            "blank": "Code cannot be empty.",
            "min_length": "Code must be 6 digits.",
            "max_length": "Code must be 6 digits.",
        },
    )


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        error_messages={
            "invalid": "Please enter a valid email address.",
            "blank": "Email cannot be empty.",
        }
    )
    code = serializers.CharField(
        max_length=6,
        min_length=6,
        error_messages={
            "blank": "Reset code cannot be empty.",
            "min_length": "Reset code must be 6 digits.",
            "max_length": "Reset code must be 6 digits.",
        },
    )
    new_password = serializers.CharField(
        write_only=True,
        error_messages={
            "blank": "Password cannot be blank.",
            "required": "Password is required.",
        },
    )

    def validate_new_password(self, value):
        validate_password(value)
        return value
