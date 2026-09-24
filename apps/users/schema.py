# apps/users/schema.py
from drf_spectacular.utils import OpenApiResponse, extend_schema

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
        description="Create a new account and return JWT access & refresh tokens.",
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
        description="Authenticate with email and password and return JWT tokens.",
        request=LoginSerializer,
        responses={
            200: TokenPayloadSerializer,
            401: OpenApiResponse(description="Invalid email or password"),
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
    "refresh_jwt": extend_schema(
        operation_id="auth_refresh",
        summary="Refresh access token",
        description=(
            "Read the refresh_token cookie and return a new short-lived access token. "
            "The browser sends the cookie automatically; no request body is required."
        ),
        request=None,
        responses={
            200: OpenApiResponse(description="New access token issued"),
            401: OpenApiResponse(description="Missing or invalid refresh token"),
        },
        tags=["Authentication"],
)
}
