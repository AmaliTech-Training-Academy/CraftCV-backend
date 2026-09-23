import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from apps.users.models import VerificationCode

DEFAULT_TTL = timedelta(minutes=15)
CODE_LENGTH = 6


def _generate_raw_code() -> str:
    upper = 10**CODE_LENGTH
    return str(secrets.randbelow(upper)).zfill(CODE_LENGTH)


def issue_code(user, purpose: str, ttl: timedelta = DEFAULT_TTL) -> str:

    VerificationCode.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(
        used_at=timezone.now()
    )

    raw = _generate_raw_code()
    VerificationCode.objects.create(
        user=user,
        purpose=purpose,
        code_hash=make_password(raw),
        expires_at=timezone.now() + ttl,
    )
    return raw


def verify_code(user, purpose: str, raw: str) -> bool:

    if not raw:
        return False

    code = (
        VerificationCode.objects.filter(user=user, purpose=purpose, used_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if code is None or not code.is_valid():
        return False
    if not check_password(raw, code.code_hash):
        return False

    code.used_at = timezone.now()
    code.save(update_fields=["used_at"])
    return True
