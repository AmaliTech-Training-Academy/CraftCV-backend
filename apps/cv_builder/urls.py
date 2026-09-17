from django.urls import path

from .views import CVDetailView, CVListCreateView

urlpatterns = [
    path("", CVListCreateView.as_view(), name="cv-list-create"),
    path("<uuid:cv_id>/", CVDetailView.as_view(), name="cv-detail"),
]
