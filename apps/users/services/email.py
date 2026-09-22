import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def send_password_reset_code(to_email: str, code: str) -> None:
    try:
        send_mail(
            subject="Your CraftCV password reset code",
            message=(
                f"Your password reset code is: {code}\n\n"
                f"It expires in 15 minutes. If you didn't request this, ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send password reset email to %s", to_email)