import hashlib
import json
from datetime import timedelta

from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    CV,
    AdditionalInformation,
    Award,
    Certification,
    Education,
    Experience,
    IdempotencyRecord,
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
from .services.cv_save import mark_cvs_as_saved, mark_user_cvs_as_saved


class UpdateRelatedCVTimestampsMixin:
    def perform_update(self, serializer):
        instance = serializer.save()
        mark_cvs_as_saved(instance.cvs.all())

    def perform_destroy(self, instance):
        affected_cv_ids = list(instance.cvs.values_list("cv_id", flat=True))

        instance.delete()

        affected_cvs = CV.objects.filter(cv_id__in=affected_cv_ids)
        mark_cvs_as_saved(affected_cvs)


class DestroyResponseMixin:
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        resource_name = instance._meta.verbose_name.title()
        self.perform_destroy(instance)

        return Response(
            {"message": f"{resource_name} deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


class SuccessResponseMixin:
    def _resource_name(self):
        resource_name = self.get_serializer_class().Meta.model._meta.verbose_name.title()
        return "CV" if resource_name == "Cv" else resource_name

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return self._add_create_success_message(response)

    def _add_create_success_message(self, response):
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


class IdempotencyKeyConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This Idempotency-Key was already used with a different request."
    default_code = "idempotency_key_conflict"


class IdempotencyKeyCreateMixin:
    idempotency_key_max_length = 255
    idempotency_key_ttl = timedelta(hours=24)

    @staticmethod
    def _request_hash(data):
        if hasattr(data, "lists"):
            data = {key: values if len(values) > 1 else values[0] for key, values in data.lists()}

        payload = json.dumps(
            data,
            cls=DjangoJSONEncoder,
            default=str,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _replay_idempotent_response(self, record, request_hash):
        if record.request_hash != request_hash:
            raise IdempotencyKeyConflict()

        return Response(
            record.response_body,
            status=record.response_status,
            headers={"Idempotent-Replayed": "true"},
        )

    def create(self, request, *args, **kwargs):
        key = request.headers.get("Idempotency-Key")
        if key is None:
            return super().create(request, *args, **kwargs)

        key = key.strip()
        if not key:
            raise ValidationError({"Idempotency-Key": "This header cannot be empty."})
        if len(key) > self.idempotency_key_max_length:
            raise ValidationError(
                {"Idempotency-Key": "This header must be 255 characters or fewer."}
            )

        endpoint = request.resolver_match.view_name or request.path
        request_hash = self._request_hash(request.data)
        now = timezone.now()
        lookup = {
            "user": request.user,
            "endpoint": endpoint,
            "key": key,
        }
        IdempotencyRecord.objects.filter(**lookup, expires_at__lte=now).delete()
        existing_record = IdempotencyRecord.objects.filter(**lookup).first()
        if existing_record is not None:
            return self._replay_idempotent_response(existing_record, request_hash)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                record = IdempotencyRecord.objects.create(
                    **lookup,
                    request_hash=request_hash,
                    expires_at=now + self.idempotency_key_ttl,
                )
                self.perform_create(serializer)

                serializer_data = serializer.data
                response = Response(
                    serializer_data,
                    status=status.HTTP_201_CREATED,
                    headers=self.get_success_headers(serializer_data),
                )
                response = self._add_create_success_message(response)
                response_body = dict(response.data)
                record.response_body = response_body
                record.response_status = response.status_code
                record.save(update_fields=["response_body", "response_status"])
        except IntegrityError:
            existing_record = IdempotencyRecord.objects.filter(**lookup).first()
            if existing_record is None:
                raise
            return self._replay_idempotent_response(existing_record, request_hash)

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


class CVDetailView(
    SuccessResponseMixin, DestroyResponseMixin, generics.RetrieveUpdateDestroyAPIView
):
    serializer_class = CVSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "cv_id"
    http_method_names = ["get", "patch", "delete", "head", "options"]

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

    def perform_update(self, serializer):
        serializer.save(last_saved_at=timezone.now())

    def patch(self, request, *args, **kwargs):
        response = self.partial_update(request, *args, **kwargs)
        response.data["message"] = "CV updated successfully"
        return response

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "CV deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


class CVDuplicateView(generics.GenericAPIView):
    serializer_class = CVSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "cv_id"

    def get_queryset(self):
        return (
            CV.objects.filter(user=self.request.user)
            .select_related("template")
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

    @staticmethod
    def _duplicate_sections(source, duplicate):
        section_names = (
            "educations",
            "experiences",
            "skills",
            "certifications",
            "languages",
            "awards",
            "additional_information",
        )

        for section_name in section_names:
            relation = getattr(source, section_name)
            section_model = relation.model
            copied_records = []

            for record in relation.all():
                values = {
                    field.attname: getattr(record, field.attname)
                    for field in section_model._meta.concrete_fields
                    if not field.primary_key
                    and not field.auto_created
                    and not getattr(field, "auto_now", False)
                    and not getattr(field, "auto_now_add", False)
                }
                if section_name == "skills":
                    values["is_cv_copy"] = True
                copied_records.append(section_model.objects.create(**values))

            getattr(duplicate, section_name).set(copied_records)

    def post(self, request, *args, **kwargs):
        source = self.get_object()

        with transaction.atomic():
            duplicate = CV.objects.create(
                user=request.user,
                template=source.template,
                title=f"Copy of {source.title}"[:150],
                professional_title=source.professional_title,
                professional_summary=source.professional_summary,
            )
            self._duplicate_sections(source, duplicate)

        serializer = self.get_serializer(duplicate)
        return Response(
            {**serializer.data, "message": "CV duplicated successfully."},
            status=status.HTTP_201_CREATED,
        )


class PersonalDetailView(generics.RetrieveUpdateAPIView, DestroyResponseMixin):
    serializer_class = PersonalDetailSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "put", "delete", "head", "options"]

    def get_object(self):
        try:
            return PersonalDetail.objects.get(user=self.request.user)
        except PersonalDetail.DoesNotExist:
            raise NotFound("Personal details have not been created yet.") from None

    def perform_update(self, serializer):
        serializer.save()
        mark_user_cvs_as_saved(self.request.user)

    def patch(self, request, *args, **kwargs):
        response = self.partial_update(request, *args, **kwargs)
        response.data["message"] = "Personal details updated successfully"

        return response

    def perform_destroy(self, instance):
        instance.delete()
        mark_user_cvs_as_saved(self.request.user)

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(
            {"message": "Personal details deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )

    def put(self, request, *args, **kwargs):
        try:
            personal_detail = PersonalDetail.objects.get(user=request.user)

        except PersonalDetail.DoesNotExist:
            serializer = self.get_serializer(data=request.data)

            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
            mark_user_cvs_as_saved(request.user)

            return Response(
                {**serializer.data, "message": "Personal details created successfully."},
                status=status.HTTP_201_CREATED,
            )

        serializer = self.get_serializer(
            personal_detail,
            data=request.data,
        )

        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            {**serializer.data, "message": "Personal details updated successfully."},
            status=status.HTTP_200_OK,
        )


class EducationListCreateView(
    IdempotencyKeyCreateMixin, SuccessResponseMixin, generics.ListCreateAPIView
):
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
    UpdateRelatedCVTimestampsMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "education_id"

    def get_queryset(self):
        return Education.objects.filter(user=self.request.user)


class ExperienceListCreateView(
    IdempotencyKeyCreateMixin, SuccessResponseMixin, generics.ListCreateAPIView
):
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
    UpdateRelatedCVTimestampsMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = ExperienceSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "experience_id"

    def get_queryset(self):
        return Experience.objects.filter(user=self.request.user)


class SkillListCreateView(
    IdempotencyKeyCreateMixin, SuccessResponseMixin, generics.ListCreateAPIView
):
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Skill.objects.filter(user=self.request.user, is_cv_copy=False)

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
    UpdateRelatedCVTimestampsMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "skill_id"

    def get_queryset(self):
        return Skill.objects.filter(user=self.request.user)


class CertificationListCreateView(
    IdempotencyKeyCreateMixin, SuccessResponseMixin, generics.ListCreateAPIView
):
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
    UpdateRelatedCVTimestampsMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = CertificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "certification_id"

    def get_queryset(self):
        return Certification.objects.filter(user=self.request.user)


class LanguageListCreateView(
    IdempotencyKeyCreateMixin, SuccessResponseMixin, generics.ListCreateAPIView
):
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
    UpdateRelatedCVTimestampsMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = LanguageSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "language_id"

    def get_queryset(self):
        return Language.objects.filter(user=self.request.user)


class AwardListCreateView(
    IdempotencyKeyCreateMixin, SuccessResponseMixin, generics.ListCreateAPIView
):
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
    UpdateRelatedCVTimestampsMixin,
    generics.RetrieveUpdateDestroyAPIView,
):
    serializer_class = AwardSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "award_id"

    def get_queryset(self):
        return Award.objects.filter(user=self.request.user)


class AdditionalInformationListCreateView(
    IdempotencyKeyCreateMixin, SuccessResponseMixin, generics.ListCreateAPIView
):
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
    UpdateRelatedCVTimestampsMixin,
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
