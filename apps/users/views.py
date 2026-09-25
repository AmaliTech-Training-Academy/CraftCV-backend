from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from drf_spectacular.utils import extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import VerificationCode
from apps.users.services.email import send_password_reset_code
from apps.users.services.verification import issue_code, verify_code

from .schema import auth_schema
from .serializers import (
    ForgotPasswordSerializer,
    LoginSerializer,
    ResetPasswordSerializer,
    UserCreateSerializer,
    UserSerializer,
    VerifyCodeSerializer,
)

User = get_user_model()

REMEMBER_ME_SECONDS = 30 * 24 * 60 * 60
SESSION_SECONDS = 12 * 60 * 60


@extend_schema_view(**auth_schema)
class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in (
            "register",
            "login",
            "forgot_password",
            "verify_code",
            "reset_password",
            "refresh",
        ):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "register":
            return UserCreateSerializer
        elif self.action == "login":
            return LoginSerializer
        elif self.action == "forgot_password":
            return ForgotPasswordSerializer
        elif self.action == "verify_code":
            return VerifyCodeSerializer
        elif self.action == "reset_password":
            return ResetPasswordSerializer
        return UserSerializer

    def _token_payload(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(self._token_payload(user), status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        remember_me = serializer.validated_data["remember_me"]

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        response = Response(
            {"user": UserSerializer(user).data, "access": str(access)}, status=status.HTTP_200_OK
        )

        max_age = REMEMBER_ME_SECONDS if remember_me else SESSION_SECONDS

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            max_age=max_age,
            httponly=True,
            secure=not settings.DEBUG,
            path="/api/auth/",
        )

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
        token = request.COOKIES.get("refresh_token")

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
            {"access": str(refresh.access_token)},
            status=status.HTTP_200_OK,
        )
