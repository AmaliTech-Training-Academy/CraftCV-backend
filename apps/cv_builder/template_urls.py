from django.urls import path

from .views import TemplateDetailView, TemplateListView

urlpatterns = [
    path("", TemplateListView.as_view(), name="template-list"),
    path("<uuid:template_id>/", TemplateDetailView.as_view(), name="template-detail"),
]
