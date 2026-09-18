from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.cv_builder.models import (
    CV,
    Education,
    Experience,
    Skill,
    Template,
)


User = get_user_model()


class CVAPITestCase(TestCase):

    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email="user@example.com",
            first_name="User1",
            last_name="U1",
            password="StrongPassword123!",
        )

        self.another_user = User.objects.create_user(
            email="another@example.com",
            first_name="User2",
            last_name="U2",
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
        self.client.force_authenticate(
            user=self.user
        )

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
    def test_authenticated_user_can_create_cv(self):
        self.authenticate()

        payload = {
            "title": "Software Engineer CV",
            "professional_summary": (
                "Backend developer interested in cloud computing."
            ),
            "template": str(self.template.template_id),
            "educations": [
                str(self.education.education_id)
            ],
            "experiences": [
                str(self.experience.experience_id)
            ],
            "skills": [
                str(self.skill.skill_id)
            ],
        }

        response = self.client.post(
            "/api/cvs/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, 201)
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

    def test_authenticated_user_can_retrieve_own_cv(self):
        self.authenticate()

        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="My CV",
            professional_summary="My summary",
        )

        response = self.client.get(
            f"/api/cvs/{cv.cv_id}/"
        )

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

        response = self.client.get(
            f"/api/cvs/{another_cv.cv_id}/"
        )

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
            "educations": [
                str(another_education.education_id)
            ],
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
        self.assertTrue(
            Education.objects.filter(
                education_id=self.education.education_id
            ).exists()
        )

    def test_deleting_education_does_not_delete_cv(self):
        self.authenticate()

        cv = CV.objects.create(
            user=self.user,
            template=self.template,
            title="CV With Education",
            professional_summary="Summary",
        )

        cv.educations.add(self.education)

        response = self.client.delete(
            f"/api/cvs/educations/{self.education.education_id}/"
        )

        self.assertEqual(response.status_code, 204)

        response = self.client.get(
            f"/api/cvs/{cv.cv_id}/"
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            CV.objects.filter(
                cv_id=cv.cv_id
            ).exists()
        )