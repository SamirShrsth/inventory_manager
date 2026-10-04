from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Profile

User = get_user_model()


class UserModelTests(TestCase):
    def test_profile_created_and_password_hashed(self):
        user = User.objects.create_user(email="a@example.com", password="UniquePass123!")
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertNotEqual(user.password, "UniquePass123!")
        self.assertTrue(user.check_password("UniquePass123!"))
        self.assertEqual(user.role, User.Roles.VIEWER)

    def test_superuser_is_admin(self):
        admin = User.objects.create_superuser(email="boss@example.com", password="UniquePass123!")
        self.assertTrue(admin.is_admin_role())
        self.assertTrue(admin.is_staff)


class AuthWebTests(TestCase):
    def test_register_login_logout(self):
        response = self.client.post(
            reverse("users:register"),
            {
                "email": "new@example.com",
                "full_name": "New User",
                "password1": "UniquePass123!",
                "password2": "UniquePass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())
        self.client.post(reverse("users:logout"))
        login = self.client.post(
            reverse("users:login"),
            {"username": "new@example.com", "password": "UniquePass123!"},
        )
        self.assertEqual(login.status_code, 302)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 302)


class AuthAPITests(APITestCase):
    def test_register_and_token_and_me(self):
        register = self.client.post(
            "/api/auth/register/",
            {
                "email": "api@example.com",
                "password": "UniquePass123!",
                "password_confirm": "UniquePass123!",
                "full_name": "API User",
            },
            format="json",
        )
        self.assertEqual(register.status_code, status.HTTP_201_CREATED)
        token = self.client.post(
            "/api/auth/token/",
            {"email": "api@example.com", "password": "UniquePass123!"},
            format="json",
        )
        self.assertEqual(token.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.data['access']}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, status.HTTP_200_OK)
        self.assertEqual(me.data["email"], "api@example.com")

    def test_protected_api_requires_auth(self):
        response = self.client.get("/api/products/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
