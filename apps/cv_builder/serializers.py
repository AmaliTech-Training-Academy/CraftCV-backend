from rest_framework import serializers

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


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ["template_id", "name", "description", "design"]
        read_only_fields = ["template_id"]


class PersonalDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalDetail
        fields = [
            "pd_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "location",
            "linkedin_url",
            "website_url",
            "github_url",
            "twitter_url",
        ]
        read_only_fields = ["pd_id"]


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            "education_id",
            "institution",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "description",
            "display_order",
        ]

        read_only_fields = ["education_id"]


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = [
            "experience_id",
            "company",
            "role",
            "location",
            "start_date",
            "end_date",
            "description",
            "display_order",
        ]
        read_only_fields = ["experience_id"]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["skill_id", "name", "display_order"]
        read_only_fields = ["skill_id"]

    def validate_name(self, value):
        user = self.context["request"].user

        queryset = Skill.objects.filter(
            user=user,
            name__iexact=value,
        )

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("You already have a skill with this name.")

        return value


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = [
            "certification_id",
            "name",
            "issuer",
            "issue_date",
            "credential_url",
            "display_order",
        ]
        read_only_fields = ["certification_id"]


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["language_id", "name", "proficiency", "display_order"]
        read_only_fields = ["language_id"]


class AwardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Award
        fields = ["award_id", "name", "issuer", "date", "description", "display_order"]
        read_only_fields = ["award_id"]


class AdditionalInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalInformation
        fields = ["additional_info_id", "title", "content", "display_order"]
        read_only_fields = ["additional_info_id"]


class CVSerializer(serializers.ModelSerializer):
    personal_detail = PersonalDetailSerializer(
        source="user.personal_detail",
        read_only=True,
    )

    educations = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Education.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "Selected education records could not be found.",
            "incorrect_type": "Please provide valid education IDs.",
        },
    )

    experiences = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Experience.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "Selected experience records could not be found.",
            "incorrect_type": "Please provide valid experience IDs.",
        },
    )

    skills = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Skill.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "Selected skills could not be found.",
            "incorrect_type": "Please provide valid skill IDs.",
        },
    )

    certifications = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Certification.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "Selected certification records could not be found.",
            "incorrect_type": "Please provide valid certification IDs.",
        },
    )

    languages = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Language.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "Selected languages could not be found.",
            "incorrect_type": "Please provide valid language IDs.",
        },
    )

    awards = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Award.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "Selected awards could not be found.",
            "incorrect_type": "Please provide valid award IDs.",
        },
    )

    additional_information = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=AdditionalInformation.objects.all(),
        required=False,
        error_messages={
            "does_not_exist": "Selected additional information records could not be found.",
            "incorrect_type": "Please provide valid additional information IDs.",
        },
    )

    template = serializers.PrimaryKeyRelatedField(
        queryset=Template.objects.all(),
        required=True,
        error_messages={
            "does_not_exist": "The selected template could not be found.",
            "incorrect_type": "Please provide a valid template ID.",
            "required": "A template is required.",
            "null": "A template cannot be empty.",
        },
    )

    class Meta:
        model = CV
        fields = (
            "cv_id",
            "title",
            "personal_detail",
            "professional_summary",
            "template",
            "educations",
            "experiences",
            "skills",
            "certifications",
            "languages",
            "awards",
            "additional_information",
            "created_at",
            "updated_at",
        )

        read_only_fields = (
            "cv_id",
            "created_at",
            "updated_at",
        )

    def validate(self, attrs):
        user = self.context["request"].user

        ownership_checks = {
            "educations": Education,
            "experiences": Experience,
            "skills": Skill,
            "certifications": Certification,
            "languages": Language,
            "awards": Award,
            "additional_information": AdditionalInformation,
        }

        for field_name, _model in ownership_checks.items():
            if field_name not in attrs:
                continue

            records = attrs[field_name]

            invalid_records = [record for record in records if record.user_id != user.id]

            if invalid_records:
                raise serializers.ValidationError(
                    {field_name: ("You can only add your own records to your CV.")}
                )

        return attrs
