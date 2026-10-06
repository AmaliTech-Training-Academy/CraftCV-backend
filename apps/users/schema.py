# apps/users/schema.py
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers

from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    TokenPayloadSerializer,
    UserCreateSerializer,
    UserSerializer,
    VerifyCodeSerializer,
)

auth_schema = {
    "register": extend_schema(
        operation_id="auth_register",
        summary="Register a new user",
        description=(
            "Create a new account and return JWT access & refresh tokens."
            "Create a new account. On success, returns JSON with user info "
            "and an access token, and sets an HttpOnly `refreshToken` cookie "
            "scoped to `Path=/api/auth/`.\n\n"
            "The frontend should call `POST /api/auth/refresh/` (with credentials) "
            "to obtain a new access token when the current one expires."
        ),
        request=UserCreateSerializer,
        responses={
            201: OpenApiResponse(
                response=TokenPayloadSerializer,
                description="User registered successfully",
            ),
        },
        tags=["Authentication"],
    ),
    "login": extend_schema(
        operation_id="auth_login",
        summary="Log in",
        description=(
            "Authenticate with email and password and return JWT tokens."
            "Authenticate with email and password. "
            "On success, returns JSON with user info and access token, "
            "and sets an HttpOnly `refreshToken` cookie at `Path=/api/auth/`."
        ),
        request=LoginSerializer,
        responses={
            200: TokenPayloadSerializer,
            401: OpenApiResponse(description="Invalid email or password"),
        },
        tags=["Authentication"],
    ),
    "logout": extend_schema(
        operation_id="auth_logout",
        summary="Log User Out",
        description="Log the current user out of the application.",
        responses={
            200: OpenApiResponse(description='returns a response as {"detail": "Logged out"}')
        },
        tags=["Authentication"],
    ),
    "me": extend_schema(
        operation_id="auth_me",
        summary="Get current user",
        description="Return the profile of the currently authenticated user.",
        responses={200: UserSerializer},
        tags=["Authentication"],
    ),
    "forgot_password": extend_schema(
        operation_id="auth_forgot_password",
        summary="Request password reset code",
        description=(
            "Send a reset code to the given email if an account exists. "
            "Always returns the same generic response to prevent account enumeration."
        ),
        request=ForgotPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Generic success"),
        },
        tags=["Authentication"],
    ),
    "verify_code": extend_schema(
        operation_id="auth_verify_code",
        summary="Verification of code sent via email",
        description=(
            "Check whether a reset code is valid without consuming it. "
            "Called before showing the new-password form. "
            "Returns the same generic error for any invalid, expired, or "
            "mismatched code to avoid leaking information."
        ),
        request=VerifyCodeSerializer,
        responses={
            200: OpenApiResponse(description="Generic success"),
        },
        tags=["Authentication"],
    ),
    "reset_password": extend_schema(
        operation_id="auth_reset_password",
        summary="Reset password with code",
        description=(
            "Verify the reset code and set a new password. "
            "Returns a generic error for invalid or expired codes."
        ),
        request=ResetPasswordSerializer,
        responses={
            200: OpenApiResponse(description="Password reset successfully"),
            400: OpenApiResponse(description="Invalid or expired code"),
        },
        tags=["Authentication"],
    ),
    "refresh": extend_schema(
        operation_id="auth_refresh",
        summary="Refresh access token",
        description=(
            "Read the refreshToken cookie and return a new short-lived access token. "
            "The browser sends the cookie automatically; no request body is required."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="RefreshTokenResponse",
                    fields={
                        "access_token": serializers.CharField(),
                    },
                ),
                description="New access token issued",
            ),
            401: OpenApiResponse(
                response=inline_serializer(
                    name="RefreshTokenError",
                    fields={
                        "error": serializers.CharField(),
                    },
                ),
                description="Missing or invalid refresh token",
            ),
        },
        tags=["Authentication"],
    ),
}
