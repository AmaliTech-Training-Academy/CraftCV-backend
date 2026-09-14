"""Smoke tests for the project wiring.

These keep the pre-push and CI test gates meaningful while the apps are still
scaffolds. Feature tests belong in the app that owns the behaviour.
"""

from django.test import TestCase
from django.urls import reverse


class SchemaEndpointTests(TestCase):
    def test_openapi_schema_is_served(self):
        response = self.client.get(reverse("schema"))

        self.assertEqual(response.status_code, 200)

    def test_swagger_ui_is_served(self):
        response = self.client.get(reverse("swagger-ui"))

        self.assertEqual(response.status_code, 200)


class AdminTests(TestCase):
    def test_admin_redirects_anonymous_user_to_login(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
