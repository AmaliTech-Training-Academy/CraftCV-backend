from django.utils import timezone


def mark_cv_as_saved(cv):
    cv.last_saved_at = timezone.now()
    cv.save(update_fields=["last_saved_at"])


def mark_cvs_as_saved(cvs):
    cvs.update(last_saved_at=timezone.now())


def mark_user_cvs_as_saved(user):
    user.cvs.update(last_saved_at=timezone.now())
