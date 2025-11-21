from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AuthenticationTests(APITestCase):
    def setUp(self):
        self.signup_url = reverse("users:signup")
        self.login_url = reverse("users:login")
        self.logout_url = reverse("users:logout")
        self.password_change_url = reverse("users:password_change")

    def test_user_can_sign_up_and_login(self):
        signup_payload = {
            "email": "new@example.com",
            "name": "New User",
            "password": "StrongPass123",
        }
        signup_response = self.client.post(self.signup_url, signup_payload, format="json")
        self.assertEqual(signup_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(signup_response.data["email"], signup_payload["email"])
        self.assertTrue(User.objects.filter(email=signup_payload["email"]).exists())

        # Session should be active after signup; logout and login again
        self.client.post(self.logout_url)
        login_response = self.client.post(
            self.login_url,
            {"email": signup_payload["email"], "password": signup_payload["password"]},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertEqual(login_response.data["email"], signup_payload["email"])

    def test_password_change_requires_correct_old_password(self):
        user = User.objects.create_user(email="user@example.com", name="User", password="OldPass123")
        self.client.force_authenticate(user=user)

        bad_response = self.client.post(
            self.password_change_url,
            {"old_password": "wrong", "new_password": "NewPass123"},
            format="json",
        )
        self.assertEqual(bad_response.status_code, status.HTTP_400_BAD_REQUEST)

        good_response = self.client.post(
            self.password_change_url,
            {"old_password": "OldPass123", "new_password": "NewPass123"},
            format="json",
        )
        self.assertEqual(good_response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPass123"))

    def test_login_rejects_invalid_credentials(self):
        User.objects.create_user(email="login@example.com", name="Login", password="ValidPass123")
        response = self.client.post(
            self.login_url,
            {"email": "login@example.com", "password": "bad"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)
