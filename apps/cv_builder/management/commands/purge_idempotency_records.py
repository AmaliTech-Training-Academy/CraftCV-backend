from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cv_builder.models import IdempotencyRecord


class Command(BaseCommand):
    help = "Delete expired CV section idempotency records."

    def handle(self, *args, **options):
        deleted_count, _ = IdempotencyRecord.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f"Deleted {deleted_count} expired idempotency record(s).")
