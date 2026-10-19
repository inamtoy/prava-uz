from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_STUDENT = "student"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [(ROLE_STUDENT, "O'quvchi"), (ROLE_ADMIN, "Admin")]

    email = models.EmailField("email", unique=True)
    role = models.CharField("rol", max_length=20, choices=ROLE_CHOICES, default=ROLE_STUDENT)

    class Meta:
        db_table = "foydalanuvchilar"
        verbose_name = "foydalanuvchi"
        verbose_name_plural = "foydalanuvchilar"

    def save(self, *args, **kwargs):
        # Superuser har doim admin roliga ega; is_staff rol bilan sinxron.
        if self.is_superuser:
            self.role = self.ROLE_ADMIN
        self.is_staff = self.role == self.ROLE_ADMIN
        super().save(*args, **kwargs)

    @property
    def is_admin_role(self):
        return self.role == self.ROLE_ADMIN
