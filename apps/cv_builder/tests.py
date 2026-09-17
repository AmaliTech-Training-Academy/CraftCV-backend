from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CV, Skill, Template


class CVApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="owner@example.com",
            password="password-123",
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com",
            password="password-123",
        )
        self.template = Template.objects.create(
            name="Professional",
            design="professional-design",
        )

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)

    def create_cv(self, *, user, title):
        return CV.objects.create(user=user, template=self.template, title=title)

    def test_list_requires_authentication(self):
        response = self.client.get(reverse("cv-list-create"))

        self.assertIn(
            response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        )

    def test_list_returns_only_the_authenticated_users_cvs(self):
        own_cv = self.create_cv(user=self.user, title="My CV")
        self.create_cv(user=self.other_user, title="Other CV")
        self.authenticate_as(self.user)

        response = self.client.get(reverse("cv-list-create"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["cv_id"] for item in response.data], [str(own_cv.cv_id)])

    def test_create_assigns_the_authenticated_user(self):
        self.authenticate_as(self.user)

        response = self.client.post(
            reverse("cv-list-create"),
            {"title": "Backend Engineer", "template": str(self.template.template_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cv = CV.objects.get(cv_id=response.data["cv_id"])
        self.assertEqual(cv.user, self.user)

    def test_create_rejects_records_owned_by_another_user(self):
        other_users_skill = Skill.objects.create(user=self.other_user, name="Python")
        self.authenticate_as(self.user)

        response = self.client.post(
            reverse("cv-list-create"),
            {
                "title": "Backend Engineer",
                "template": str(self.template.template_id),
                "skills": [str(other_users_skill.skill_id)],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("skills", response.data)

    def test_detail_is_scoped_to_the_authenticated_user(self):
        other_users_cv = self.create_cv(user=self.other_user, title="Private CV")
        self.authenticate_as(self.user)

        response = self.client.get(reverse("cv-detail", kwargs={"cv_id": other_users_cv.cv_id}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_partially_updates_a_cv(self):
        cv = self.create_cv(user=self.user, title="Old title")
        self.authenticate_as(self.user)

        response = self.client.put(
            reverse("cv-detail", kwargs={"cv_id": cv.cv_id}),
            {"title": "New title"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cv.refresh_from_db()
        self.assertEqual(cv.title, "New title")

    def test_named_routes_include_the_expected_path_separators(self):
        cv = self.create_cv(user=self.user, title="My CV")

        self.assertEqual(reverse("cv-list-create"), "/api/cvs/")
        self.assertEqual(
            reverse("cv-detail", kwargs={"cv_id": cv.cv_id}),
            f"/api/cvs/{cv.cv_id}/",
        )

    def test_a_jwt_access_token_authenticates_a_cv_request(self):
        access_token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.get(reverse("cv-list-create"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
