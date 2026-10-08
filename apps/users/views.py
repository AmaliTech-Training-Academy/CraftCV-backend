from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from drf_spectacular.utils import extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import VerificationCode
from apps.users.services.email import send_email_verification_code, send_password_reset_code
from apps.users.services.verification import issue_code, verify_code

from .schema import auth_schema
from .serializers import (
    EmptySerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    UserCreateSerializer,
    UserSerializer,
    VerifyCodeSerializer,
    VerifyEmailSerializer,
)

User = get_user_model()

REMEMBER_ME_SECONDS = timedelta(days=30)
DEFAULT_REFRESH_LIFETIME = jwt_settings.REFRESH_TOKEN_LIFETIME


@extend_schema_view(**auth_schema)
class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action is None or self.action in (
            "register",
            "login",
            "logout",
            "forgot_password",
            "verify_code",
            "reset_password",
            "refresh",
            "verify_email",
        ):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        action = self.action or self.action_map.get("post")

        if action == "register":
            return UserCreateSerializer
        elif action == "login":
            return LoginSerializer
        elif action == "forgot_password":
            return ForgotPasswordSerializer
        elif action == "verify_code":
            return VerifyCodeSerializer
        elif action == "reset_password":
            return ResetPasswordSerializer
        elif action == "verify_email":
            return VerifyEmailSerializer
        elif action in ("refresh", "logout"):
            return EmptySerializer
        return UserSerializer

    def _set_refresh_cookie(self, response, refresh_token, lifetime: timedelta):
        response.set_cookie(
            key="refreshToken",
            value=str(refresh_token),
            max_age=int(lifetime.total_seconds()),
            httponly=True,
            secure=False,
            samesite="Lax",
            path="/",
        )

    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        raw = issue_code(user, VerificationCode.Purpose.EMAIL_VERIFICATION)
        send_email_verification_code(user.email, raw)

        return Response(
            {
                "message": "Account created. Please check your email for a verification code.",
                "email": user.email,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="verify-email",
        permission_classes=[AllowAny],
    )
    def verify_email(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        GENERIC_ERROR = "Invalid or expired verification code."

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return Response({"error": GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        if user.email_verified:
            return Response({"message": "Email already verified."}, status=status.HTTP_200_OK)

        if not verify_code(user, VerificationCode.Purpose.EMAIL_VERIFICATION, code):
            return Response({"error": GENERIC_ERROR}, status=status.HTTP_400_BAD_REQUEST)

        user.email_verified = True
        user.save(update_fields=["email_verified"])

        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                "message": "Email verified successfully.",
                "user": UserSerializer(user).data,
                "access_token": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )
        self._set_refresh_cookie(response, refresh, DEFAULT_REFRESH_LIFETIME)
        return response

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get("email")
        password = serializer.validated_data.get("password")
        remember_me = serializer.validated_data.get("remember_me")

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.email_verified:
            return Response(
                {
                    "error": "Email not verified.",
                    "code": "email_not_verified",
                    "email": user.email,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        response = Response(
            {
                "user": UserSerializer(user).data,
                "access_token": str(access),
            },
            status=status.HTTP_200_OK,
        )

        max_age = REMEMBER_ME_SECONDS if remember_me else DEFAULT_REFRESH_LIFETIME

        self._set_refresh_cookie(response, refresh, max_age)

        return response

    @action(detail=False, methods=["post"], url_path="logout", permission_classes=[IsAuthenticated])
    def logout(self, request):
        refresh_token = request.COOKIES.get("refreshToken")

        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                return Response(
                    {"detail": "Invalid or expired refresh token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        response = Response({"detail": "Logged out."}, status=status.HTTP_200_OK)
        response.delete_cookie("refreshToken", path="/", samesite="Lax")
        return response

    @action(
        detail=False,
        methods=["get"],
        url_path="me",
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        return Response(self.get_serializer(request.user).data)

    @action(
        detail=False,
        methods=["post"],
        url_path="forgot-password",
        permission_classes=[AllowAny],
    )
    def forgot_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()

        if user is not None:
            raw = issue_code(user, VerificationCode.Purpose.PASSWORD_RESET)
            send_password_reset_code(user.email, raw)

        return Response(
            {
                "message": (
                    "If an account exists for this email, a password reset code has been sent."
                )
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="verify-code",
        permission_classes=[AllowAny],
    )
    def verify_code(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()

        if user is None or not verify_code(
            user,
            VerificationCode.Purpose.PASSWORD_RESET,
            serializer.validated_data["code"],
            consume=False,
        ):
            return Response(
                {"error": "Invalid or expired reset code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"valid": True}, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=["post"],
        url_path="reset-password",
        permission_classes=[AllowAny],
    )
    def reset_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]
        new_password = serializer.validated_data["new_password"]

        GENERIC_ERROR = "Invalid or expired reset code."

        user = User.objects.filter(email__iexact=email).first()

        if user is None:
            return Response(
                {"error": GENERIC_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not verify_code(user, VerificationCode.Purpose.PASSWORD_RESET, code):
            return Response(
                {"error": GENERIC_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response(
            {"message": "Password reset successfully."},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="refresh",
        permission_classes=[AllowAny],
    )
    def refresh(self, request):
        token = request.COOKIES.get("refreshToken")
        print(token)

        if not token:
            return Response({"error": "No refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(token)
        except TokenError:
            return Response(
                {"error": "Invalid or expired refresh token."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {"access_token": str(refresh.access_token)},
            status=status.HTTP_200_OK,
        )
