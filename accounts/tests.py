from django.contrib.auth import get_user
from django.test import TestCase
from django.urls import reverse

from .models import User


class AccountTests(TestCase):
    def test_register_logs_user_in(self):
        resp = self.client.post(reverse("register"), {
            "first_name": "Ali",
            "username": "ali",
            "email": "Ali@Example.com",
            "password1": "Kuchli-parol-2026",
            "password2": "Kuchli-parol-2026",
        })
        self.assertRedirects(resp, reverse("topic_list"))
        user = User.objects.get(username="ali")
        self.assertEqual(user.email, "ali@example.com")
        self.assertEqual(user.role, User.ROLE_STUDENT)
        self.assertFalse(user.is_staff)
        self.assertEqual(get_user(self.client).pk, user.pk)

    def test_register_rejects_duplicate_email(self):
        User.objects.create_user("vali", "vali@example.com", "Kuchli-parol-2026")
        resp = self.client.post(reverse("register"), {
            "first_name": "V", "username": "vali2", "email": "VALI@example.com",
            "password1": "Kuchli-parol-2026", "password2": "Kuchli-parol-2026",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "allaqachon")

    def test_login_with_email(self):
        User.objects.create_user("bek", "bek@example.com", "Kuchli-parol-2026")
        resp = self.client.post(reverse("login"), {"username": "bek@example.com", "password": "Kuchli-parol-2026"})
        self.assertRedirects(resp, reverse("topic_list"))
        self.assertTrue(get_user(self.client).is_authenticated)

    def test_login_with_username(self):
        User.objects.create_user("bek", "bek@example.com", "Kuchli-parol-2026")
        resp = self.client.post(reverse("login"), {"username": "bek", "password": "Kuchli-parol-2026"})
        self.assertRedirects(resp, reverse("topic_list"))

    def test_wrong_password_rejected(self):
        User.objects.create_user("bek", "bek@example.com", "Kuchli-parol-2026")
        resp = self.client.post(reverse("login"), {"username": "bek@example.com", "password": "xato"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(get_user(self.client).is_authenticated)

    def test_password_is_hashed(self):
        user = User.objects.create_user("bek", "bek@example.com", "Kuchli-parol-2026")
        self.assertNotEqual(user.password, "Kuchli-parol-2026")
        self.assertTrue(user.password.startswith("pbkdf2_sha256$"))
        self.assertTrue(user.check_password("Kuchli-parol-2026"))

    def test_logout_requires_post(self):
        user = User.objects.create_user("bek", "bek@example.com", "Kuchli-parol-2026")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("home"))
