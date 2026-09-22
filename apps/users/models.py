import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.db import models
from django.utils import timezone
from django.conf import settings

from .managers import CustomUserManager


# Create your models here.
class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        unique=True, error_messages={"unique": "A user with this email already exists"}
    )
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    other_name = models.CharField(max_length=150, blank=True)
    agree_to_terms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class VerificationCode(models.Model):
    class Purpose(models.TextChoices):
        PASSWORD_RESET = "password_reset", "Password Reset"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verification_codes"
    )
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.purpose} - {self.created_at:%Y-%m-%d %H:%M}"

    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()
