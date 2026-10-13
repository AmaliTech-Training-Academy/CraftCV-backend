from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from apps.cv_builder.models import (
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

User = get_user_model()


class CVAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="user@example.com",
            password="StrongPassword123!",
        )

        self.another_user = User.objects.create_user(
            email="another@example.com",
            password="StrongPassword123!",
        )

        self.template, _ = Template.objects.get_or_create(
            name="Professional",
            defaults={"description": "Professional CV template"},
        )

        self.education = Education.objects.create(
            user=self.user,
            institution="University of Mines and Technology",
            degree="BSc",
            field_of_study="Computer Science and Engineering",
            location="Tarkwa, Ghana",
            start_date="2024-10-01",
            description="Computer science studies",
            display_order=0,
        )

        self.experience = Experience.objects.create(
            user=self.user,
            company="ABC Technologies",
            role="Backend Developer Intern",
            location="Takoradi, Ghana",
            start_date="2026-06-01",
            description="Developed backend APIs",
            display_order=0,
        )

        self.skill = Skill.objects.create(
            user=self.user,
            name="Python",
            display_order=0,
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def test_personal_detail_put_requires_complete_data_for_existing_record(self):
        self.authenticate()
        personal_detail = PersonalDetail.objects.create(
            user=self.user,
            first_name="First",
            last_name="Last",
            email="user@example.com",
            phone="1234567890",
            location="Accra",
            linkedin_url="https://linkedin.com/in/first",
        )

        put_response = self.client.put(
            "/api/cvs/personal-details/",
            {"first_name": "Updated"},
            format="json",
        )

        self.assertEqual(put_response.status_code, 400)
        self.assertIn("last_name", put_response.data)
        self.assertIn("email", put_response.data)

        patch_response = self.client.patch(
            "/api/cvs/personal-details/",
            {"first_name": "Updated"},
            format="json",
        )

        self.assertEqual(patch_response.status_code, 200)
        personal_detail.refresh_from_db()
        self.assertEqual(personal_detail.first_name, "Updated")
        self.assertEqual(personal_detail.last_name, "Last")

    def test_personal_detail_put_updates_existing_record_with_complete_data(self):
        self.authenticate()
        personal_detail = PersonalDetail.objects.create(
            user=self.user,
            first_name="First",
            last_name="Last",
            email="user@example.com",
            phone="1234567890",
            location="Accra",
            linkedin_url="https://linkedin.com/in/first",
        )

        response = self.client.put(
            "/api/cvs/personal-details/",
            {
                "first_name": "Updated",
                "last_name": "Person",
                "email": "updated@example.com",
                "phone": "0987654321",
                "location": "Kumasi",
                "linkedin_url": "",
                "website_url": "",
                "github_url": "",
                "twitter_url": "",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        personal_detail.refresh_from_db()
        self.assertEqual(personal_detail.first_name, "Updated")
        self.assertEqual(personal_detail.last_name, "Person")
        self.assertEqual(personal_detail.email, "updated@example.com")
        self.assertEqual(personal_detail.linkedin_url, "")

    def test_deleting_personal_details_preserves_cvs_and_updates_timestamps(self):
        self.authenticate()
        PersonalDetail.objects.create(
            user=self.user,
            first_name="First",
            last_name="Last",
            email="user@example.com",
            phone="1234567890",
            location="Accra",
        )
        previous_saved_at = timezone.now() - timedelta(days=1)
        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="My CV",
            last_saved_at=previous_saved_at,
        )

        response = self.client.delete("/api/cvs/personal-details/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(PersonalDetail.objects.filter(user=self.user).exists())
        cv.refresh_from_db()
        self.assertGreater(cv.last_saved_at, previous_saved_at)
        self.assertTrue(CV.objects.filter(cv_id=cv.cv_id).exists())

    def test_unauthenticated_user_cannot_list_cvs(self):
        response = self.client.get("/api/cvs/")

        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_list_templates(self):
        self.authenticate()

        response = self.client.get("/api/templates/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            {
                "template_id": str(self.template.template_id),
                "name": self.template.name,
                "description": self.template.description,
                "slug": self.template.slug,
            },
            response.data,
        )

    def test_authenticated_user_can_create_and_list_cv_sections(self):
        self.authenticate()

        section_cases = [
            (
                "educations",
                {
                    "institution": "University of Ghana",
                    "degree": "MSc",
                    "field_of_study": "Information Technology",
                    "location": "Accra, Ghana",
                    "start_date": "2025-10-01",
                },
                Education,
            ),
            (
                "experiences",
                {
                    "company": "CraftCV",
                    "role": "Software Engineer",
                    "start_date": "2025-10-01",
                },
                Experience,
            ),
            ("skills", {"name": "Django", "level": "Advanced"}, Skill),
            (
                "certifications",
                {
                    "name": "AWS Certified Developer",
                    "issuer": "Amazon Web Services",
                    "issue_date": "2025-10-01",
                },
                Certification,
            ),
            (
                "languages",
                {"name": "English", "proficiency": "native"},
                Language,
            ),
            ("awards", {"name": "Backend Excellence Award"}, Award),
            (
                "additional-information",
                {"title": "Availability", "content": "Available immediately."},
                AdditionalInformation,
            ),
        ]

        for endpoint, payload, model in section_cases:
            with self.subTest(endpoint=endpoint):
                create_response = self.client.post(
                    f"/api/cvs/{endpoint}/",
                    payload,
                    format="json",
                )

                self.assertEqual(create_response.status_code, 201)
                self.assertTrue(model.objects.filter(user=self.user).exists())

                list_response = self.client.get(f"/api/cvs/{endpoint}/")

                self.assertEqual(list_response.status_code, 200)
                created_data = dict(create_response.data)
                created_data.pop("message")
                self.assertIn(created_data, list_response.data)

    def test_section_create_idempotency_key_replays_original_response(self):
        self.authenticate()

        section_cases = [
            (
                "educations",
                {
                    "institution": "University of Ghana",
                    "degree": "MSc",
                    "field_of_study": "Information Technology",
                    "location": "Accra, Ghana",
                    "start_date": "2025-10-01",
                },
                Education,
            ),
            (
                "experiences",
                {
                    "company": "CraftCV",
                    "role": "Software Engineer",
                    "start_date": "2025-10-01",
                },
                Experience,
            ),
            ("skills", {"name": "Django", "level": "Advanced"}, Skill),
            (
                "certifications",
                {
                    "name": "AWS Certified Developer",
                    "issuer": "Amazon Web Services",
                    "issue_date": "2025-10-01",
                },
                Certification,
            ),
            ("languages", {"name": "English", "proficiency": "native"}, Language),
            ("awards", {"name": "Engineering Award"}, Award),
            (
                "additional-information",
                {"title": "Availability", "content": "Available immediately."},
                AdditionalInformation,
            ),
        ]

        for endpoint, payload, model in section_cases:
            with self.subTest(endpoint=endpoint):
                initial_count = model.objects.filter(user=self.user).count()
                url = f"/api/cvs/{endpoint}/"
                headers = {"HTTP_IDEMPOTENCY_KEY": "section-create-replay"}

                first_response = self.client.post(url, payload, format="json", **headers)
                replay_response = self.client.post(url, payload, format="json", **headers)

                self.assertEqual(first_response.status_code, 201)
                self.assertEqual(replay_response.status_code, 201)
                self.assertEqual(replay_response.data, first_response.data)
                self.assertEqual(replay_response.headers["Idempotent-Replayed"], "true")
                self.assertEqual(model.objects.filter(user=self.user).count(), initial_count + 1)

    def test_idempotency_key_cannot_be_reused_with_different_payload(self):
        self.authenticate()
        headers = {"HTTP_IDEMPOTENCY_KEY": "education-create"}

        first_response = self.client.post(
            "/api/cvs/educations/",
            {
                "institution": "University of Ghana",
                "degree": "MSc",
                "field_of_study": "Information Technology",
                "location": "Accra, Ghana",
                "start_date": "2025-10-01",
            },
            format="json",
            **headers,
        )
        conflicting_response = self.client.post(
            "/api/cvs/educations/",
            {
                "institution": "University of Ghana",
                "degree": "PhD",
                "field_of_study": "Information Technology",
                "location": "Accra, Ghana",
                "start_date": "2025-10-01",
            },
            format="json",
            **headers,
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(conflicting_response.status_code, 409)
        self.assertEqual(Education.objects.filter(user=self.user).count(), 2)

    def test_idempotency_keys_are_scoped_to_the_authenticated_user(self):
        self.authenticate()
        payload = {
            "institution": "University of Ghana",
            "degree": "MSc",
            "field_of_study": "Information Technology",
            "location": "Accra, Ghana",
            "start_date": "2025-10-01",
        }
        headers = {"HTTP_IDEMPOTENCY_KEY": "user-scoped-create"}

        first_response = self.client.post(
            "/api/cvs/educations/",
            payload,
            format="json",
            **headers,
        )
        self.client.force_authenticate(user=self.another_user)
        second_response = self.client.post(
            "/api/cvs/educations/",
            payload,
            format="json",
            **headers,
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 201)
        self.assertNotEqual(
            first_response.data["education_id"],
            second_response.data["education_id"],
        )
        self.assertEqual(IdempotencyRecord.objects.count(), 2)

    def test_invalid_section_payload_does_not_reserve_idempotency_key(self):
        self.authenticate()
        headers = {"HTTP_IDEMPOTENCY_KEY": "education-invalid-then-valid"}

        invalid_response = self.client.post(
            "/api/cvs/educations/",
            {
                "institution": "University of Ghana",
                "degree": "MSc",
                "field_of_study": "Information Technology",
                "location": "Accra, Ghana",
                "start_date": "2018-13-01",
            },
            format="json",
            **headers,
        )
        valid_response = self.client.post(
            "/api/cvs/educations/",
            {
                "institution": "University of Ghana",
                "degree": "MSc",
                "field_of_study": "Information Technology",
                "location": "Accra, Ghana",
                "start_date": "2018-12-01",
            },
            format="json",
            **headers,
        )

        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(valid_response.status_code, 201)
        self.assertEqual(IdempotencyRecord.objects.count(), 1)

    def test_empty_or_oversized_idempotency_key_is_rejected(self):
        self.authenticate()

        for key in ("   ", "k" * 256):
            with self.subTest(key_length=len(key)):
                response = self.client.post(
                    "/api/cvs/educations/",
                    {},
                    format="json",
                    HTTP_IDEMPOTENCY_KEY=key,
                )

                self.assertEqual(response.status_code, 400)
        self.assertEqual(IdempotencyRecord.objects.count(), 0)

    def test_expired_idempotency_key_can_be_reused(self):
        self.authenticate()
        key = "education-expiry"
        other_users_expired_record = IdempotencyRecord.objects.create(
            user=self.another_user,
            endpoint="cv_builder:education-list-create",
            key=key,
            request_hash="c" * 64,
            expires_at=timezone.now() - timedelta(days=1),
        )
        payload = {
            "institution": "University of Ghana",
            "degree": "MSc",
            "field_of_study": "Information Technology",
            "location": "Accra, Ghana",
            "start_date": "2025-10-01",
        }
        response = self.client.post(
            "/api/cvs/educations/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        record = IdempotencyRecord.objects.get(user=self.user, key=key)
        record.expires_at = timezone.now() - timedelta(seconds=1)
        record.save(update_fields=["expires_at"])
        initial_education_count = Education.objects.filter(user=self.user).count()

        reused_response = self.client.post(
            "/api/cvs/educations/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(reused_response.status_code, 201)
        self.assertNotEqual(response.data["education_id"], reused_response.data["education_id"])
        self.assertEqual(
            Education.objects.filter(user=self.user).count(),
            initial_education_count + 1,
        )
        self.assertTrue(IdempotencyRecord.objects.filter(pk=other_users_expired_record.pk).exists())

    def test_integrity_error_race_replays_the_winning_response(self):
        self.authenticate()
        key = "education-race"
        payload = {
            "institution": "University of Ghana",
            "degree": "MSc",
            "field_of_study": "Information Technology",
            "location": "Accra, Ghana",
            "start_date": "2025-10-01",
        }
        first_response = self.client.post(
            "/api/cvs/educations/",
            payload,
            format="json",
            HTTP_IDEMPOTENCY_KEY=key,
        )
        record = IdempotencyRecord.objects.get(key=key)
        lookup = {"user": self.user, "endpoint": record.endpoint, "key": key}
        original_filter = IdempotencyRecord.objects.filter
        exact_lookup_count = 0

        def hide_existing_record_for_initial_lookup(*args, **kwargs):
            nonlocal exact_lookup_count
            if kwargs == lookup:
                exact_lookup_count += 1
                if exact_lookup_count == 1:
                    return original_filter(*args, **kwargs).none()
            return original_filter(*args, **kwargs)

        with (
            patch.object(
                IdempotencyRecord.objects,
                "filter",
                side_effect=hide_existing_record_for_initial_lookup,
            ),
            patch.object(IdempotencyRecord.objects, "create", side_effect=IntegrityError),
        ):
            raced_response = self.client.post(
                "/api/cvs/educations/",
                payload,
                format="json",
                HTTP_IDEMPOTENCY_KEY=key,
            )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(raced_response.status_code, 201)
        self.assertEqual(raced_response.data, first_response.data)
        self.assertEqual(raced_response.headers["Idempotent-Replayed"], "true")
        self.assertEqual(Education.objects.filter(user=self.user).count(), 2)

    def test_purge_idempotency_records_command_removes_only_expired_records(self):
        expired_record = IdempotencyRecord.objects.create(
            user=self.user,
            endpoint="cv_builder:education-list-create",
            key="expired",
            request_hash="a" * 64,
            expires_at=timezone.now() - timedelta(days=1),
        )
        live_record = IdempotencyRecord.objects.create(
            user=self.user,
            endpoint="cv_builder:education-list-create",
            key="live",
            request_hash="b" * 64,
            expires_at=timezone.now() + timedelta(days=1),
        )

        call_command("purge_idempotency_records", stdout=StringIO())

        self.assertFalse(IdempotencyRecord.objects.filter(pk=expired_record.pk).exists())
        self.assertTrue(IdempotencyRecord.objects.filter(pk=live_record.pk).exists())

    def test_cors_preflight_allows_idempotency_key_header(self):
        response = self.client.options(
            "/api/cvs/educations/",
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type,idempotency-key",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "idempotency-key",
            response.headers["access-control-allow-headers"].lower(),
        )
        self.assertIn(
            "idempotent-replayed",
            response.headers["access-control-expose-headers"].lower(),
        )

    def test_authenticated_user_can_create_cv(self):
        self.authenticate()

        payload = {
            "title": "Software Engineer CV",
            "professional_title": "Senior Backend Engineer",
            "professional_summary": ("Backend developer interested in cloud computing."),
            "template": str(self.template.template_id),
            "educations": [str(self.education.education_id)],
            "experiences": [str(self.experience.experience_id)],
            "skills": [str(self.skill.skill_id)],
        }

        response = self.client.post(
            "/api/cvs/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["message"], "CV created successfully.")
        self.assertEqual(
            response.data["title"],
            "Software Engineer CV",
        )
        self.assertEqual(
            response.data["professional_title"],
            "Senior Backend Engineer",
        )

        self.assertEqual(
            len(response.data["educations"]),
            1,
        )

        self.assertEqual(
            len(response.data["experiences"]),
            1,
        )

        self.assertEqual(
            len(response.data["skills"]),
            1,
        )

    def test_user_can_duplicate_cv_with_independent_sections(self):
        self.authenticate()
        certification = Certification.objects.create(
            user=self.user,
            name="AWS Developer",
            issuer="Amazon",
            issue_date="2025-01-01",
        )
        language = Language.objects.create(
            user=self.user,
            name="English",
            proficiency=Language.Proficiency.FLUENT,
        )
        award = Award.objects.create(user=self.user, name="Engineering Award")
        additional_information = AdditionalInformation.objects.create(
            user=self.user,
            title="Availability",
            content="Available immediately",
        )
        source = CV.objects.create(
            user=self.user,
            template=self.template,
            title="General CV",
            professional_title="Senior Backend Engineer",
            professional_summary="Original summary",
        )
        source.educations.add(self.education)
        source.experiences.add(self.experience)
        source.skills.add(self.skill)
        source.certifications.add(certification)
        source.languages.add(language)
        source.awards.add(award)
        source.additional_information.add(additional_information)

        response = self.client.post(f"/api/cvs/{source.cv_id}/duplicate/")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["message"], "CV duplicated successfully.")
        self.assertEqual(response.data["title"], "Copy of General CV")
        self.assertEqual(response.data["professional_title"], source.professional_title)
        self.assertEqual(response.data["professional_summary"], source.professional_summary)
        self.assertEqual(response.data["template"], self.template.template_id)
        duplicate = CV.objects.get(cv_id=response.data["cv_id"])

        for section_name in (
            "educations",
            "experiences",
            "skills",
            "certifications",
            "languages",
            "awards",
            "additional_information",
        ):
            with self.subTest(section=section_name):
                original_record = getattr(source, section_name).get()
                copied_record = getattr(duplicate, section_name).get()
                self.assertNotEqual(original_record.pk, copied_record.pk)
                for field in original_record._meta.concrete_fields:
                    if (
                        field.primary_key
                        or field.auto_created
                        or getattr(field, "auto_now", False)
                        or getattr(field, "auto_now_add", False)
                        or (section_name == "skills" and field.name == "is_cv_copy")
                    ):
                        continue
                    with self.subTest(section=section_name, field=field.name):
                        self.assertEqual(
                            getattr(original_record, field.attname),
                            getattr(copied_record, field.attname),
                        )

        copied_education = duplicate.educations.get()
        update_response = self.client.patch(
            f"/api/cvs/educations/{copied_education.education_id}/",
            {"degree": "MSc"},
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.education.refresh_from_db()
        copied_education.refresh_from_db()
        self.assertEqual(self.education.degree, "BSc")
        self.assertEqual(copied_education.degree, "MSc")

        copied_skill = duplicate.skills.get()
        skill_update_response = self.client.patch(
            f"/api/cvs/skills/{copied_skill.skill_id}/",
            {"name": "Tailored Python"},
            format="json",
        )
        self.assertEqual(skill_update_response.status_code, 200)
        self.skill.refresh_from_db()
        copied_skill.refresh_from_db()
        self.assertEqual(self.skill.name, "Python")
        self.assertEqual(copied_skill.name, "Tailored Python")

        delete_response = self.client.delete(f"/api/cvs/{duplicate.cv_id}/")

        self.assertEqual(delete_response.status_code, 204)
        self.assertTrue(CV.objects.filter(cv_id=source.cv_id).exists())
        self.assertEqual(source.educations.get().degree, "BSc")
        self.assertEqual(source.skills.get().name, "Python")

    def test_user_cannot_duplicate_another_users_cv(self):
        self.authenticate()
        another_users_cv = CV.objects.create(
            user=self.another_user,
            template=self.template,
            title="Private CV",
        )

        response = self.client.post(f"/api/cvs/{another_users_cv.cv_id}/duplicate/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["message"], "CV resource not found.")
        self.assertFalse(CV.objects.filter(user=self.user).exists())
        self.assertTrue(CV.objects.filter(cv_id=another_users_cv.cv_id).exists())

    def test_user_cannot_duplicate_a_missing_cv(self):
        self.authenticate()

        response = self.client.post("/api/cvs/00000000-0000-0000-0000-000000000000/duplicate/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No CV matches the given query.")
        self.assertEqual(response.data["message"], "CV resource not found.")
        self.assertFalse(CV.objects.filter(user=self.user).exists())

    def test_unauthenticated_user_cannot_duplicate_cv(self):
        source = CV.objects.create(
            user=self.user,
            template=self.template,
            title="Private CV",
        )

        response = self.client.post(f"/api/cvs/{source.cv_id}/duplicate/")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.data["message"],
            "Authentication is required to access CV data.",
        )
        self.assertEqual(CV.objects.filter(user=self.user).count(), 1)

    def test_empty_cv_list_returns_message(self):
        self.authenticate()

        response = self.client.get("/api/cvs/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "You have not created any CVs yet.")
        self.assertEqual(response.data["data"], [])

    def test_invalid_cv_data_returns_validation_response(self):
        self.authenticate()

        response = self.client.post(
            "/api/cvs/",
            {"professional_summary": "Missing title and template"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Invalid CV data.")
        self.assertIn("title", response.data)
        self.assertIn("template", response.data)

    def test_missing_cv_returns_custom_error_response(self):
        self.authenticate()

        response = self.client.get(
            "/api/cvs/00000000-0000-0000-0000-000000000000/",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "No CV matches the given query.")
        self.assertEqual(response.data["message"], "CV resource not found.")

    def test_authenticated_user_can_retrieve_own_cv(self):
        self.authenticate()

        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="My CV",
            professional_summary="My summary",
        )

        response = self.client.get(f"/api/cvs/{cv.cv_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["cv_id"],
            str(cv.cv_id),
        )

    def test_user_can_delete_own_cv(self):
        self.authenticate()
        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="My CV",
        )

        response = self.client.delete(f"/api/cvs/{cv.cv_id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(CV.objects.filter(cv_id=cv.cv_id).exists())

    def test_user_cannot_delete_another_users_cv(self):
        self.authenticate()
        another_cv = CV.objects.create(
            user=self.another_user,
            template=self.template,
            title="Private CV",
        )

        response = self.client.delete(f"/api/cvs/{another_cv.cv_id}/")

        self.assertEqual(response.status_code, 404)
        self.assertTrue(CV.objects.filter(cv_id=another_cv.cv_id).exists())

    def test_patching_cv_saves_draft_and_updates_last_saved_at(self):
        self.authenticate()

        previous_saved_at = timezone.now() - timedelta(days=1)
        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="Draft CV",
            professional_summary="Original summary",
            last_saved_at=previous_saved_at,
        )

        response = self.client.patch(
            f"/api/cvs/{cv.cv_id}/",
            {
                "title": "Updated draft CV",
                "professional_summary": "Updated draft summary",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "CV updated successfully")
        self.assertEqual(response.data["title"], "Updated draft CV")
        self.assertEqual(
            response.data["professional_summary"],
            "Updated draft summary",
        )

        cv.refresh_from_db()
        self.assertGreater(cv.last_saved_at, previous_saved_at)
        self.assertEqual(
            parse_datetime(response.data["last_saved_at"]),
            cv.last_saved_at,
        )

    def test_retrieving_cv_returns_saved_draft_and_last_saved_at(self):
        self.authenticate()

        saved_at = timezone.now() - timedelta(days=1)
        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="Saved draft CV",
            professional_summary="Saved draft summary",
            last_saved_at=saved_at,
        )
        cv.educations.add(self.education)

        response = self.client.get(f"/api/cvs/{cv.cv_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Saved draft CV")
        self.assertEqual(
            response.data["professional_summary"],
            "Saved draft summary",
        )
        self.assertEqual(len(response.data["educations"]), 1)
        self.assertEqual(
            parse_datetime(response.data["last_saved_at"]),
            saved_at,
        )

    def test_professional_title_can_be_updated_without_changing_cv_title(self):
        self.authenticate()
        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="General CV",
            professional_title="Backend Engineer",
        )

        response = self.client.patch(
            f"/api/cvs/{cv.cv_id}/",
            {"professional_title": "Senior Backend Engineer"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "General CV")
        self.assertEqual(response.data["professional_title"], "Senior Backend Engineer")
        cv.refresh_from_db()
        self.assertEqual(cv.title, "General CV")
        self.assertEqual(cv.professional_title, "Senior Backend Engineer")

    def test_user_cannot_access_another_users_cv(self):
        self.authenticate()

        another_cv = CV.objects.create(
            user=self.another_user,
            template=self.template,
            title="Private CV",
            professional_summary="Private information",
        )

        response = self.client.get(f"/api/cvs/{another_cv.cv_id}/")

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_attach_another_users_education(self):
        self.authenticate()

        another_education = Education.objects.create(
            user=self.another_user,
            institution="Another University",
            degree="BSc",
            field_of_study="Computer Science",
            location="Koforidua, Ghana",
            start_date="2024-10-01",
        )

        payload = {
            "title": "Invalid CV",
            "professional_summary": "Testing ownership",
            "template": str(self.template.template_id),
            "educations": [str(another_education.education_id)],
        }

        response = self.client.post(
            "/api/cvs/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("educations", response.data)

    def test_updating_one_section_preserves_other_sections(self):
        self.authenticate()

        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="Original CV",
            professional_summary="Original summary",
        )

        cv.educations.add(self.education)
        cv.experiences.add(self.experience)
        cv.skills.add(self.skill)

        response = self.client.patch(
            f"/api/cvs/{cv.cv_id}/",
            {
                "professional_summary": "Updated summary",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "CV updated successfully")

        self.assertEqual(
            response.data["professional_summary"],
            "Updated summary",
        )

        self.assertEqual(
            len(response.data["educations"]),
            1,
        )

        self.assertEqual(
            len(response.data["experiences"]),
            1,
        )

        self.assertEqual(
            len(response.data["skills"]),
            1,
        )

    def test_explicit_empty_list_removes_cv_relationship(self):
        self.authenticate()

        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="CV With Education",
            professional_summary="Summary",
        )

        cv.educations.add(self.education)

        response = self.client.patch(
            f"/api/cvs/{cv.cv_id}/",
            {
                "educations": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["educations"],
            [],
        )

        # The master Education record still exists.
        self.assertTrue(Education.objects.filter(education_id=self.education.education_id).exists())

    def test_deleting_education_does_not_delete_cv(self):
        self.authenticate()

        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="CV With Education",
            professional_summary="Summary",
        )

        cv.educations.add(self.education)

        response = self.client.delete(f"/api/cvs/educations/{self.education.education_id}/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, {"message": "Education deleted successfully."})

        response = self.client.get(f"/api/cvs/{cv.cv_id}/")

        self.assertEqual(response.status_code, 200)

        self.assertTrue(CV.objects.filter(cv_id=cv.cv_id).exists())

    def test_cv_can_contain_multiple_education_entries(self):
        self.authenticate()

        education_1 = Education.objects.create(
            user=self.user,
            institution="University One",
            degree="BSc",
            field_of_study="Computer Science",
            location="Accra, Ghana",
            start_date="2020-10-01",
        )

        education_2 = Education.objects.create(
            user=self.user,
            institution="University Two",
            degree="MSc",
            field_of_study="Computer Science",
            location="Kumasi, Ghana",
            start_date="2024-10-01",
        )

        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="My CV",
        )

        cv.educations.add(education_1, education_2)

        response = self.client.get(f"/api/cvs/{cv.cv_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["educations"]), 2)

    def test_cv_can_contain_multiple_experience_entries(self):
        self.authenticate()

        experience_1 = Experience.objects.create(
            user=self.user,
            company="Company One",
            role="Developer",
            start_date="2024-01-01",
        )

        experience_2 = Experience.objects.create(
            user=self.user,
            company="Company Two",
            role="Engineer",
            start_date="2025-01-01",
        )

        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="My CV",
        )

        cv.experiences.add(experience_1, experience_2)

        response = self.client.get(f"/api/cvs/{cv.cv_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["experiences"]), 2)

    def test_removing_education_from_cv_does_not_delete_education(self):
        self.authenticate()

        education = Education.objects.create(
            user=self.user,
            institution="University",
            degree="BSc",
            field_of_study="Computer Science",
            location="Ho, Ghana",
            start_date="2024-01-01",
        )

        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="My CV",
        )

        cv.educations.add(education)

        response = self.client.patch(
            f"/api/cvs/{cv.cv_id}/",
            {
                "educations": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["educations"], [])
        self.assertTrue(Education.objects.filter(education_id=education.education_id).exists())
