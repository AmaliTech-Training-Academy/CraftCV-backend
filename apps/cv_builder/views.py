from rest_framework import generics
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


class CVListCreateView(generics.ListCreateAPIView):
    serializer_class = CVSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            CV.objects
            .filter(user=self.request.user)
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
    http_method_names = ["get", "put", "head", "options"]

    def get_queryset(self):
        return (
            CV.objects
            .filter(user=self.request.user)
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
        return self.update(
            request,
            *args,
            partial=True,
            **kwargs,
        )


class PersonalDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = PersonalDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return PersonalDetail.objects.get(
                user=self.request.user
            )
        except PersonalDetail.DoesNotExist:
            raise NotFound(
                "Personal details have not been created yet."
            )

    def put(self, request, *args, **kwargs):
        try:
            personal_detail = PersonalDetail.objects.get(
                user=request.user
            )

        except PersonalDetail.DoesNotExist:
            serializer = self.get_serializer(
                data=request.data
            )

            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)

            return Response(
                serializer.data,
                status=201,
            )

        serializer = self.get_serializer(
            personal_detail,
            data=request.data,
            partial=True,
        )

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            serializer.data,
            status=200,
        )

class EducationListCreateView(generics.ListCreateAPIView):
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Education.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EducationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "education_id"

    def get_queryset(self):
        return Education.objects.filter(
            user=self.request.user
        )

class ExperienceListCreateView(generics.ListCreateAPIView):
    serializer_class = ExperienceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Experience.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ExperienceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExperienceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "experience_id"

    def get_queryset(self):
        return Experience.objects.filter(
            user=self.request.user
        )

class SkillListCreateView(generics.ListCreateAPIView):
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Skill.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SkillDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "skill_id"

    def get_queryset(self):
        return Skill.objects.filter(
            user=self.request.user
        )

class CertificationListCreateView(generics.ListCreateAPIView):
    serializer_class = CertificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Certification.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CertificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CertificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "certification_id"

    def get_queryset(self):
        return Certification.objects.filter(
            user=self.request.user
        )

class LanguageListCreateView(generics.ListCreateAPIView):
    serializer_class = LanguageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Language.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LanguageDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LanguageSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "language_id"

    def get_queryset(self):
        return Language.objects.filter(
            user=self.request.user
        )

class AwardListCreateView(generics.ListCreateAPIView):
    serializer_class = AwardSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Award.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AwardDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AwardSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "award_id"

    def get_queryset(self):
        return Award.objects.filter(
            user=self.request.user
        )

class AdditionalInformationListCreateView(generics.ListCreateAPIView):
    serializer_class = AdditionalInformationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AdditionalInformation.objects.filter(
            user=self.request.user
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AdditionalInformationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AdditionalInformationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "additional_info_id"

    def get_queryset(self):
        return AdditionalInformation.objects.filter(
            user=self.request.user
        )
class TemplateListView(generics.ListAPIView):
    serializer_class = TemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Template.objects.all()

class TemplateDetailView(generics.RetrieveAPIView):
    serializer_class= TemplateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "template_id"

    def get_queryset(self):
        return Template.objects.all()