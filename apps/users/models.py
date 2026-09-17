import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.db import models

from .managers import CustomUserManager


# Create your models here.
class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        unique=True, error_messages={"unique": "A user with this email already exists"}
    )
    agree_to_terms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = CustomUserManager()

    USERNAME_FIELD = "email"

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email
