from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cv_builder.models import (
    AdditionalInformation,
    Education,
    Experience,
    Skill,
)

User = get_user_model()


class MasterDataAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="faith@example.com", password="StrongPassword123!", agree_to_terms=True
        )

        self.another_user = User.objects.create_user(
            email="emma@example.com", password="StrongPassword123!", agree_to_terms=True
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def test_user_can_create_education(self):
        self.authenticate()

        payload = {
            "institution": "University of Mines and Technology",
            "degree": "BSc",
            "field_of_study": "Computer Science and Engineering",
            "start_date": "2024-10-01",
            "end_date": None,
            "description": "Computer science studies",
            "display_order": 0,
        }

        response = self.client.post(
            "/api/cvs/educations/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["institution"],
            "University of Mines and Technology",
        )

        self.assertTrue(
            Education.objects.filter(
                user=self.user,
                institution="University of Mines and Technology",
            ).exists()
        )

    def test_user_can_have_multiple_education_entries(self):
        self.authenticate()

        education_1 = {
            "institution": "University of Mines and Technology",
            "degree": "BSc",
            "field_of_study": "Computer Science",
            "start_date": "2024-10-01",
            "end_date": None,
            "description": "First education",
            "display_order": 0,
        }

        education_2 = {
            "institution": "Takoradi Technical University",
            "degree": "HND",
            "field_of_study": "Electrical Engineering",
            "start_date": "2020-10-01",
            "end_date": "2023-06-30",
            "description": "Second education",
            "display_order": 1,
        }

        response_1 = self.client.post(
            "/api/cvs/educations/",
            education_1,
            format="json",
        )

        response_2 = self.client.post(
            "/api/cvs/educations/",
            education_2,
            format="json",
        )

        self.assertEqual(response_1.status_code, 201)
        self.assertEqual(response_2.status_code, 201)

        self.assertEqual(
            Education.objects.filter(user=self.user).count(),
            2,
        )

    def test_user_can_update_education(self):
        self.authenticate()

        education = Education.objects.create(
            user=self.user,
            institution="Old University",
            degree="BSc",
            field_of_study="Computer Science",
            start_date="2024-10-01",
        )

        response = self.client.patch(
            f"/api/cvs/educations/{education.education_id}/",
            {
                "institution": "University of Mines and Technology",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        education.refresh_from_db()

        self.assertEqual(
            education.institution,
            "University of Mines and Technology",
        )

    def test_user_can_delete_individual_education(self):
        self.authenticate()

        education_1 = Education.objects.create(
            user=self.user,
            institution="University One",
            degree="BSc",
            field_of_study="Computer Science",
            start_date="2024-10-01",
        )

        education_2 = Education.objects.create(
            user=self.user,
            institution="University Two",
            degree="HND",
            field_of_study="Electrical Engineering",
            start_date="2020-10-01",
        )

        response = self.client.delete(f"/api/cvs/educations/{education_1.education_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Education deleted successfully.")

        self.assertFalse(Education.objects.filter(education_id=education_1.education_id).exists())

        self.assertTrue(Education.objects.filter(education_id=education_2.education_id).exists())

    def test_invalid_education_data_is_rejected(self):
        self.authenticate()

        payload = {
            "institution": "",
            "degree": "",
            "field_of_study": "",
            "start_date": "not-a-date",
        }

        response = self.client.post(
            "/api/cvs/educations/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn("institution", response.data)
        self.assertIn("degree", response.data)
        self.assertIn("field_of_study", response.data)
        self.assertIn("start_date", response.data)

    def test_education_end_date_is_optional(self):
        self.authenticate()

        payload = {
            "institution": "University of Mines and Technology",
            "degree": "BSc",
            "field_of_study": "Computer Science",
            "start_date": "2024-10-01",
        }

        response = self.client.post(
            "/api/cvs/educations/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["end_date"])

    def test_user_can_create_experience(self):
        self.authenticate()

        payload = {
            "company": "ABC Technologies",
            "role": "Backend Developer Intern",
            "location": "Takoradi, Ghana",
            "start_date": "2026-06-01",
            "end_date": None,
            "description": "Developed backend APIs",
            "display_order": 0,
        }

        response = self.client.post(
            "/api/cvs/experiences/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["company"],
            "ABC Technologies",
        )

    def test_user_can_have_multiple_experience_entries(self):
        self.authenticate()

        experience_1 = {
            "company": "Company One",
            "role": "Backend Developer",
            "location": "Takoradi",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "description": "Backend development",
            "display_order": 0,
        }

        experience_2 = {
            "company": "Company Two",
            "role": "Software Engineer",
            "location": "Accra",
            "start_date": "2026-01-01",
            "end_date": None,
            "description": "Software engineering",
            "display_order": 1,
        }

        response_1 = self.client.post(
            "/api/cvs/experiences/",
            experience_1,
            format="json",
        )

        response_2 = self.client.post(
            "/api/cvs/experiences/",
            experience_2,
            format="json",
        )

        self.assertEqual(response_1.status_code, 201)
        self.assertEqual(response_2.status_code, 201)

        self.assertEqual(
            Experience.objects.filter(user=self.user).count(),
            2,
        )

    def test_user_can_update_experience(self):
        self.authenticate()

        experience = Experience.objects.create(
            user=self.user,
            company="Old Company",
            role="Developer",
            start_date="2025-01-01",
        )

        response = self.client.patch(
            f"/api/cvs/experiences/{experience.experience_id}/",
            {
                "company": "New Company",
                "role": "Senior Developer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        experience.refresh_from_db()

        self.assertEqual(experience.company, "New Company")
        self.assertEqual(experience.role, "Senior Developer")

    def test_user_can_delete_individual_experience(self):
        self.authenticate()

        experience_1 = Experience.objects.create(
            user=self.user,
            company="Company One",
            role="Developer",
            start_date="2025-01-01",
        )

        experience_2 = Experience.objects.create(
            user=self.user,
            company="Company Two",
            role="Engineer",
            start_date="2026-01-01",
        )

        response = self.client.delete(f"/api/cvs/experiences/{experience_1.experience_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Experience deleted successfully.")

        self.assertFalse(
            Experience.objects.filter(experience_id=experience_1.experience_id).exists()
        )

        self.assertTrue(
            Experience.objects.filter(experience_id=experience_2.experience_id).exists()
        )

    def test_invalid_experience_data_is_rejected(self):
        self.authenticate()

        payload = {
            "company": "",
            "role": "",
            "start_date": "invalid-date",
        }

        response = self.client.post(
            "/api/cvs/experiences/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 400)

        self.assertIn("company", response.data)
        self.assertIn("role", response.data)
        self.assertIn("start_date", response.data)

    def test_experience_end_date_is_optional(self):
        self.authenticate()

        payload = {
            "company": "ABC Technologies",
            "role": "Backend Developer",
            "start_date": "2026-01-01",
        }

        response = self.client.post(
            "/api/cvs/experiences/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["end_date"])

    def test_user_can_create_skill(self):
        self.authenticate()

        response = self.client.post(
            "/api/cvs/skills/",
            {
                "name": "Python",
                "display_order": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Python")

    def test_user_can_have_multiple_skills(self):
        self.authenticate()

        skills = ["Python", "Django", "PostgreSQL"]

        for skill in skills:
            response = self.client.post(
                "/api/cvs/skills/",
                {
                    "name": skill,
                    "display_order": 0,
                },
                format="json",
            )

            self.assertEqual(response.status_code, 201)

        self.assertEqual(
            Skill.objects.filter(user=self.user).count(),
            3,
        )

    def test_duplicate_skill_is_rejected(self):
        self.authenticate()

        Skill.objects.create(
            user=self.user,
            name="Python",
        )

        response = self.client.post(
            "/api/cvs/skills/",
            {
                "name": "python",
                "display_order": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_user_can_delete_individual_skill(self):
        self.authenticate()

        skill = Skill.objects.create(
            user=self.user,
            name="Python",
        )

        response = self.client.delete(f"/api/cvs/skills/{skill.skill_id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "Skill deleted successfully.")

        self.assertFalse(Skill.objects.filter(skill_id=skill.skill_id).exists())

    def test_certification_can_be_created(self):
        self.authenticate()

        response = self.client.post(
            "/api/cvs/certifications/",
            {
                "name": "AWS Cloud Engineering",
                "issuer": "CloudWithShad",
                "issue_date": "2026-01-15",
                "credential_url": "",
                "display_order": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_language_can_be_created(self):
        self.authenticate()

        response = self.client.post(
            "/api/cvs/languages/",
            {
                "name": "English",
                "proficiency": "fluent",
                "display_order": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_invalid_language_proficiency_is_rejected(self):
        self.authenticate()

        response = self.client.post(
            "/api/cvs/languages/",
            {
                "name": "English",
                "proficiency": "expert",
                "display_order": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("proficiency", response.data)

    def test_award_can_be_created_without_optional_fields(self):
        self.authenticate()

        response = self.client.post(
            "/api/cvs/awards/",
            {
                "name": "Best Developer Award",
                "issuer": "",
                "date": None,
                "description": "",
                "display_order": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

    def test_additional_information_can_be_created(self):
        self.authenticate()

        response = self.client.post(
            "/api/cvs/additional-information/",
            {
                "title": "Interests",
                "content": "Open source, cloud computing and AI.",
                "display_order": 0,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        self.assertTrue(
            AdditionalInformation.objects.filter(
                user=self.user,
                title="Interests",
            ).exists()
        )

    def test_user_cannot_access_another_users_education(self):
        self.authenticate()

        education = Education.objects.create(
            user=self.another_user,
            institution="Private University",
            degree="BSc",
            field_of_study="Computer Science",
            start_date="2024-01-01",
        )

        response = self.client.get(f"/api/cvs/educations/{education.education_id}/")

        self.assertEqual(response.status_code, 404)

    def test_user_cannot_access_another_users_experience(self):
        self.authenticate()

        experience = Experience.objects.create(
            user=self.another_user,
            company="Private Company",
            role="Developer",
            start_date="2024-01-01",
        )

        response = self.client.get(f"/api/cvs/experiences/{experience.experience_id}/")

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_user_cannot_access_education(self):
        response = self.client.get("/api/cvs/educations/")

        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_user_cannot_access_experience(self):
        response = self.client.get("/api/cvs/experiences/")

        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_user_cannot_access_skills(self):
        response = self.client.get("/api/cvs/skills/")

        self.assertEqual(response.status_code, 401)
