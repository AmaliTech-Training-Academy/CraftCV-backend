from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class UserCreationTest(APITestCase):
    def setUp(self):
        self.url = reverse("auth-register")
        self.valid_payload = {
            "email": "faith@example.com",
            "password": "StrongPass123!",
            "firstName": "Faith",
            "lastName": "Gbadegbe",
            "otherName": "Etornam",
            "agreeToTerms": True,
        }

    def test_registration_success(self):
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email=self.valid_payload["email"]).exists())

    def test_registration_duplicate_email_fails(self):
        self.client.post(self.url, self.valid_payload, format="json")
        response = self.client.post(self.url, self.valid_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_registration_password_is_hashed(self):
        self.client.post(self.url, self.valid_payload, format="json")
        user = User.objects.get(email=self.valid_payload["email"])
        self.assertNotEqual(user.password, self.valid_payload["password"])
        self.assertTrue(user.check_password(self.valid_payload["password"]))


class LoginTest(APITestCase):
    def setUp(self):
        self.url = reverse("auth-login")
        self.email = "faith@example.com"
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(
            email=self.email,
            password=self.password,
            first_name="Faith",
            last_name="Gbadegbe",
            agree_to_terms=True,
        )

    def test_login_success(self):
        response = self.client.post(
            self.url,
            {"email": self.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], self.email)

    def test_login_wrong_password(self):
        response = self.client.post(
            self.url,
            {"email": self.email, "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_nonexistent_email(self):
        response = self.client.post(
            self.url,
            {"email": "nobody@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_missing_fields(self):
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertIn("password", response.data)

    def test_login_token_is_valid(self):
        login = self.client.post(
            self.url,
            {"email": self.email, "password": self.password},
            format="json",
        )
        access = login.data["access"]

        me_response = self.client.get(
            reverse("auth-me"),
            HTTP_AUTHORIZATION=f"JWT {access}",
        )
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["email"], self.email)
