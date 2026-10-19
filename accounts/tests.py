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
        self.assertRedirects(resp, reverse("profile"))
        self.assertTrue(get_user(self.client).is_authenticated)

    def test_login_with_username(self):
        User.objects.create_user("bek", "bek@example.com", "Kuchli-parol-2026")
        resp = self.client.post(reverse("login"), {"username": "bek", "password": "Kuchli-parol-2026"})
        self.assertRedirects(resp, reverse("profile"))

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


class RoleBasedLoginTests(TestCase):
    """Yagona login: admin -> /admin/, o'quvchi -> profil; next faqat ruxsat etilgan bo'lsa."""

    PASSWORD = "Kuchli-parol-2026"

    def setUp(self):
        self.student = User.objects.create_user("talaba", "talaba@example.com", self.PASSWORD)
        self.admin = User.objects.create_user("boss", "boss@example.com", self.PASSWORD, role=User.ROLE_ADMIN)
        self.root = User.objects.create_superuser("root", "root@example.com", self.PASSWORD)

    def login(self, username, next_url=None):
        url = reverse("login") + (f"?next={next_url}" if next_url else "")
        data = {"username": username, "password": self.PASSWORD}
        if next_url:
            data["next"] = next_url
        return self.client.post(url, data)

    def test_student_login_goes_to_profile(self):
        self.assertRedirects(self.login("talaba"), reverse("profile"))

    def test_admin_login_goes_to_admin(self):
        self.assertRedirects(self.login("boss"), reverse("admin:index"))

    def test_superuser_login_goes_to_admin(self):
        self.assertEqual(self.root.role, User.ROLE_ADMIN)  # createsuperuser -> role=admin
        self.assertRedirects(self.login("root@example.com"), reverse("admin:index"))

    def test_student_next_admin_is_ignored(self):
        self.assertRedirects(self.login("talaba", "/admin/"), reverse("profile"))

    def test_student_next_site_page_is_kept(self):
        self.assertRedirects(self.login("talaba", "/mavzular/"), reverse("topic_list"))

    def test_admin_next_admin_page_is_kept(self):
        self.assertRedirects(self.login("boss", "/admin/quiz/question/"), "/admin/quiz/question/")

    def test_external_next_is_ignored(self):
        self.assertRedirects(self.login("talaba", "https://evil.com/"), reverse("profile"))
        self.client.logout()
        self.assertRedirects(self.login("boss", "https://evil.com/admin/"), reverse("admin:index"))

    def test_admin_login_page_redirects_to_unified_login(self):
        resp = self.client.get("/admin/login/?next=/admin/quiz/question/")
        self.assertRedirects(resp, reverse("login") + "?next=%2Fadmin%2Fquiz%2Fquestion%2F", fetch_redirect_response=False)

    def test_guest_admin_goes_to_login_with_next(self):
        resp = self.client.get("/admin/", follow=True)
        self.assertEqual(resp.redirect_chain[-1][0], reverse("login") + "?next=%2Fadmin%2F")
        self.assertTemplateUsed(resp, "accounts/login.html")
        self.assertNotContains(resp, 'id="login-form"')  # Django admin login formasi emas

    def test_student_admin_goes_to_profile_with_message(self):
        self.client.force_login(self.student)
        resp = self.client.get("/admin/", follow=True)
        self.assertEqual(resp.redirect_chain[-1][0], reverse("profile"))
        self.assertContains(resp, "faqat administratorlar kira oladi")

    def test_logged_in_login_page_redirects_by_role(self):
        self.client.force_login(self.student)
        self.assertRedirects(self.client.get(reverse("login")), reverse("profile"))
        self.assertRedirects(self.client.get(reverse("register")), reverse("profile"))
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.get(reverse("login")), reverse("admin:index"))
        self.assertRedirects(self.client.get(reverse("register")), reverse("admin:index"))

    def test_admin_can_use_student_side(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("topic_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("exam_start")).status_code, 200)
        self.assertContains(self.client.get(reverse("profile")), "Boshqaruv paneli")

    def test_admin_logout_goes_home(self):
        self.client.force_login(self.admin)
        self.assertRedirects(self.client.post(reverse("admin:logout")), reverse("home"))

    def test_register_cannot_create_admin(self):
        resp = self.client.post(reverse("register"), {
            "first_name": "Hiyla", "username": "hiyla", "email": "hiyla@example.com",
            "password1": self.PASSWORD, "password2": self.PASSWORD,
            "role": "admin", "is_staff": "on", "is_superuser": "on",
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="hiyla")
        self.assertEqual(user.role, User.ROLE_STUDENT)
        self.assertFalse(user.is_staff or user.is_superuser or user.is_admin_role)

    def test_role_change_syncs_is_staff(self):
        self.student.role = User.ROLE_ADMIN
        self.student.save()
        self.student.refresh_from_db()
        self.assertTrue(self.student.is_staff and self.student.is_superuser)
        self.student.role = User.ROLE_STUDENT
        self.student.save()
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_staff or self.student.is_superuser)
