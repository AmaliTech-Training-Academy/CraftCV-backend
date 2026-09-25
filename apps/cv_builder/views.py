from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CV,
    AdditionalInformation,
    Award,
    Certification,
    Education,
    Experience,
    Language,
    PersonalDetail,
    Skill,
    Template,
)
from .serializers import (
    AdditionalInformationSerializer,
    AwardSerializer,
    CertificationSerializer,
    CVSerializer,
    EducationSerializer,
    ExperienceSerializer,
    LanguageSerializer,
    PersonalDetailSerializer,
    SkillSerializer,
    TemplateSerializer,
)


class DestroyResponseMixin:
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        resource_name = instance._meta.verbose_name.title()
        self.perform_destroy(instance)

        return Response(
            {"message": f"{resource_name} deleted successfully."},
            status=200,
        )


class SuccessResponseMixin:
    def _resource_name(self):
        resource_name = self.get_serializer_class().Meta.model._meta.verbose_name.title()
        return "CV" if resource_name == "Cv" else resource_name

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data["message"] = f"{self._resource_name()} created successfully."
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response.data["message"] = f"{self._resource_name()} retrieved successfully."
        return response

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        response.data["message"] = f"{self._resource_name()} updated successfully."
        return response


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

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return Response(
                {
                    "message": "You have not created any CVs yet.",
                    "data": [],
                },
                status=response.status_code,
            )

        return response

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data["message"] = "CV created successfully."
        return response


class CVDetailView(SuccessResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CVSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "cv_id"
    http_method_names = ["get", "put", "head", "options"]

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
        response = self.update(
            request,
            *args,
            partial=True,
            **kwargs,
        )
        return response


class PersonalDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PersonalDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return PersonalDetail.objects.get(user=self.request.user)
        except PersonalDetail.DoesNotExist:
            raise NotFound("Personal details have not been created yet.") from None

    def put(self, request, *args, **kwargs):
        try:
            personal_detail = PersonalDetail.objects.get(user=request.user)

        except PersonalDetail.DoesNotExist:
            serializer = self.get_serializer(data=request.data)

            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)

            return Response(
                {**serializer.data, "message": "Personal details created successfully."},
                status=status.HTTP_201_CREATED,
            )

        serializer = self.get_serializer(
            personal_detail,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {**serializer.data, "message": "Personal details updated successfully."},
            status=status.HTTP_200_OK,
        )


class EducationListCreateView(SuccessResponseMixin, generics.ListCreateAPIView):
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Education.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return Response(
                {
                    "message": "You have not added any education yet.",
                    "data": [],
                },
                status=response.status_code,
            )

        return response


class EducationDetailView(
    SuccessResponseMixin,
    DestroyResponseMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "education_id"

    def get_queryset(self):
        return Education.objects.filter(user=self.request.user)


class ExperienceListCreateView(SuccessResponseMixin, generics.ListCreateAPIView):
    serializer_class = ExperienceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Experience.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return Response(
                {
                    "message": "You have not added any experience yet.",
                    "data": [],
                },
                status=response.status_code,
            )

        return response


class ExperienceDetailView(
    SuccessResponseMixin,
    DestroyResponseMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = ExperienceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "experience_id"

    def get_queryset(self):
        return Experience.objects.filter(user=self.request.user)


class SkillListCreateView(SuccessResponseMixin, generics.ListCreateAPIView):
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Skill.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return Response(
                {
                    "message": "You have not added any skill yet.",
                    "data": [],
                },
                status=response.status_code,
            )

        return response


class SkillDetailView(
    SuccessResponseMixin,
    DestroyResponseMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "skill_id"

    def get_queryset(self):
        return Skill.objects.filter(user=self.request.user)


class CertificationListCreateView(SuccessResponseMixin, generics.ListCreateAPIView):
    serializer_class = CertificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certification.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return Response(
                {
                    "message": "You have not added any certificate yet.",
                    "data": [],
                },
                status=response.status_code,
            )

        return response


class CertificationDetailView(
    SuccessResponseMixin,
    DestroyResponseMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = CertificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "certification_id"

    def get_queryset(self):
        return Certification.objects.filter(user=self.request.user)


class LanguageListCreateView(SuccessResponseMixin, generics.ListCreateAPIView):
    serializer_class = LanguageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Language.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return Response(
                {
                    "message": "You have not added any language yet.",
                    "data": [],
                },
                status=response.status_code,
            )

        return response


class LanguageDetailView(
    SuccessResponseMixin,
    DestroyResponseMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = LanguageSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "language_id"

    def get_queryset(self):
        return Language.objects.filter(user=self.request.user)


class AwardListCreateView(SuccessResponseMixin, generics.ListCreateAPIView):
    serializer_class = AwardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Award.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return Response(
                {
                    "message": "You have not added any award yet.",
                    "data": [],
                },
                status=response.status_code,
            )

        return response


class AwardDetailView(
    SuccessResponseMixin,
    DestroyResponseMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = AwardSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "award_id"

    def get_queryset(self):
        return Award.objects.filter(user=self.request.user)


class AdditionalInformationListCreateView(SuccessResponseMixin, generics.ListCreateAPIView):
    serializer_class = AdditionalInformationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AdditionalInformation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return Response(
                {
                    "message": "You have not added any additional information yet.",
                    "data": [],
                },
                status=response.status_code,
            )

        return response


class AdditionalInformationDetailView(
    SuccessResponseMixin,
    DestroyResponseMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = AdditionalInformationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "additional_info_id"

    def get_queryset(self):
        return AdditionalInformation.objects.filter(user=self.request.user)


class TemplateListView(SuccessResponseMixin, generics.ListAPIView):
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Template.objects.all()

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if not response.data:
            return Response(
                {
                    "message": "No templates are available yet.",
                    "data": [],
                },
                status=response.status_code,
            )

        return response


class TemplateDetailView(SuccessResponseMixin, generics.RetrieveAPIView):
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "template_id"

    def get_queryset(self):
        return Template.objects.all()
