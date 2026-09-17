# Create your views here.
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import CV
from .serializers import CVSerializer


class CVListCreateView(generics.ListCreateAPIView):
    serializer_class = CVSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            CV.objects.filter(user=self.request.user)
            .select_related(
                "template",
                "user",
                "user__personal_detail",
            )
            .prefetch_related(
                "educations",
                "experiences",
                "skills",
                "certifications",
                "languages",
                "awards",
                "additional_information",
            )
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CVDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = CVSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "cv_id"

    def get_queryset(self):
        return (
            CV.objects.filter(user=self.request.user)
            .select_related(
                "template",
                "user",
                "user__personal_detail",
            )
            .prefetch_related(
                "educations",
                "experiences",
                "skills",
                "certifications",
                "languages",
                "awards",
                "additional_information",
            )
        )

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, partial=True, **kwargs)
