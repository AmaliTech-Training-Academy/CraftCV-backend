import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from .managers import CustomUserManager

# Create your models here.

class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, error_messages={
            'unique': 'A user with this email already exists'
        })
    username = models.CharField(
            max_length=150,
            unique=True,
            blank=True,
            default=""
        )
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return self.email
    def save(self, *args, **kwargs):
        if self.email:
            self.username = self.email.lower()

        if not self.username:
            self.username = self.email

        super().save(*args, **kwargs)
