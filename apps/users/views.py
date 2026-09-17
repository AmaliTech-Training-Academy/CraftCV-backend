from django.contrib.auth import authenticate, get_user_model
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    LoginSerializer,
    TokenPayloadSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.action in ("register", "login"):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == "register":
            return UserCreateSerializer
        elif self.action == "login":
            return LoginSerializer
        return UserSerializer

    def _token_payload(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "user": UserSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }

    @extend_schema(
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
    )
    @action(detail=False, methods=["post"], url_path="register")
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(self._token_payload(user), status=status.HTTP_201_CREATED)

    @extend_schema(
        operation_id="auth_login",
        summary="Log in",
        description="Authenticate with email and password and return JWT tokens.",
        request=LoginSerializer,
        responses={
            200: TokenPayloadSerializer,
            401: OpenApiResponse(description="Invalid email or password"),
        },
        tags=["Authentication"],
    )
    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(self._token_payload(user), status=status.HTTP_200_OK)

    @extend_schema(
        operation_id="auth_me",
        summary="Get current user",
        description="Return the profile of the currently authenticated user.",
        responses={200: UserSerializer},
        tags=["Authentication"],
    )
    @action(
        detail=False,
        methods=["get"],
        url_path="me",
        authentication_classes=[JWTAuthentication],
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        return Response(self.get_serializer(request.user).data)
