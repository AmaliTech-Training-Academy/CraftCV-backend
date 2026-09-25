from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cv_builder.models import (
    CV,
    AdditionalInformation,
    Award,
    Certification,
    Education,
    Experience,
    Language,
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

        self.template = Template.objects.create(
            name="Professional",
            description="Professional CV template",
            design="professional",
        )

        self.education = Education.objects.create(
            user=self.user,
            institution="University of Mines and Technology",
            degree="BSc",
            field_of_study="Computer Science and Engineering",
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

    def test_unauthenticated_user_cannot_list_cvs(self):
        response = self.client.get("/api/cvs/")

        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_list_templates(self):
        self.authenticate()

        response = self.client.get("/api/templates/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0],
            {
                "template_id": str(self.template.template_id),
                "name": "Professional",
                "description": "Professional CV template",
                "design": "professional",
            },
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
            ("skills", {"name": "Django"}, Skill),
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

    def test_authenticated_user_can_create_cv(self):
        self.authenticate()

        payload = {
            "title": "Software Engineer CV",
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

        response = self.client.put(
            f"/api/cvs/{cv.cv_id}/",
            {
                "professional_summary": "Updated summary",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"], "CV updated successfully.")

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

        response = self.client.put(
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

        self.assertEqual(response.status_code, 200)
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
            start_date="2020-10-01",
        )

        education_2 = Education.objects.create(
            user=self.user,
            institution="University Two",
            degree="MSc",
            field_of_study="Computer Science",
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
        start_date="2024-01-01",
    )

    cv = CV.objects.create(
        user=self.user,
        template=self.template,
        title="My CV",
    )

    cv.educations.add(education)

    response = self.client.put(
        f"/api/cvs/{cv.cv_id}/",
        {
            "educations": [],
        },
        format="json",
    )

    self.assertEqual(response.status_code, 200)

    self.assertEqual(response.data["educations"], [])

    self.assertTrue(Education.objects.filter(education_id=education.education_id).exists())
