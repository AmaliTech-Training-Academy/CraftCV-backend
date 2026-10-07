# apps/users/validators.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_password_validators.password_history.password_validation import (
    UniquePasswordsValidator,
)


class CustomUniquePasswordsValidator(UniquePasswordsValidator):
    def validate(self, password, user=None):
        try:
            super().validate(password, user)
        except ValidationError:
            raise ValidationError(
                _("You've already used this password on your account. Please choose a new one."),
                code="password_used_before",
            ) from None
