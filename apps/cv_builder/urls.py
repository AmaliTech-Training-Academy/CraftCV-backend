from django.urls import path

from .views import (
    AdditionalInformationDetailView,
    AdditionalInformationListCreateView,
    AwardDetailView,
    AwardListCreateView,
    CertificationDetailView,
    CertificationListCreateView,
    CVDetailView,
    CVListCreateView,
    EducationDetailView,
    EducationListCreateView,
    ExperienceDetailView,
    ExperienceListCreateView,
    LanguageDetailView,
    LanguageListCreateView,
    PersonalDetailView,
    SkillDetailView,
    SkillListCreateView,
)

urlpatterns = [
    path("personal-details/", PersonalDetailView.as_view(), name="personal-detail"),
    path("educations/", EducationListCreateView.as_view(), name="education-list-create"),
    path("educations/<uuid:education_id>/", EducationDetailView.as_view(), name="education-detail"),
    path("experiences/", ExperienceListCreateView.as_view(), name="experience-list-create"),
    path(
        "experiences/<uuid:experience_id>/",
        ExperienceDetailView.as_view(),
        name="experience-detail",
    ),
    path("skills/", SkillListCreateView.as_view(), name="skill-list-create"),
    path("skills/<uuid:skill_id>/", SkillDetailView.as_view(), name="skill-detail"),
    path(
        "certifications/", CertificationListCreateView.as_view(), name="certification-list-create"
    ),
    path(
        "certifications/<uuid:certification_id>/",
        CertificationDetailView.as_view(),
        name="certification-detail",
    ),
    path("languages/", LanguageListCreateView.as_view(), name="language-list-create"),
    path("languages/<uuid:language_id>/", LanguageDetailView.as_view(), name="language-detail"),
    path("awards/", AwardListCreateView.as_view(), name="award-list-create"),
    path("awards/<uuid:award_id>/", AwardDetailView.as_view(), name="award-detail"),
    path(
        "additional-information/",
        AdditionalInformationListCreateView.as_view(),
        name="additional-information-list-create",
    ),
    path(
        "additional-information/<uuid:additional_info_id>/",
        AdditionalInformationDetailView.as_view(),
        name="additional-information-detail",
    ),
    path("", CVListCreateView.as_view(), name="cv-list-create"),
    path("<uuid:cv_id>/", CVDetailView.as_view(), name="cv-detail"),
]
