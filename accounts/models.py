from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.ROLE_ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    ROLE_STUDENT = "student"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [(ROLE_STUDENT, "Oʻquvchi"), (ROLE_ADMIN, "Admin")]

    email = models.EmailField("email", unique=True)
    role = models.CharField("rol", max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)

    objects = UserManager()

    class Meta:
        db_table = "foydalanuvchilar"
        verbose_name = "foydalanuvchi"
        verbose_name_plural = "foydalanuvchilar"

    def save(self, *args, **kwargs):
        # Rol — yagona manba: admin roli panelga to'liq kirish huquqini beradi
        # (is_superuser va is_staff roldan hosil bo'ladi; createsuperuser role="admin" qo'yadi).
        self.is_superuser = self.role == self.ROLE_ADMIN
        self.is_staff = self.is_admin_role
        super().save(*args, **kwargs)

    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN or self.is_superuser
