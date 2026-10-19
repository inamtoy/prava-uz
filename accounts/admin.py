from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "first_name", "role", "is_staff", "date_joined")
    list_filter = ("role", "is_staff", "is_superuser", "is_active")
    fieldsets = BaseUserAdmin.fieldsets + (("Rol", {"fields": ("role",)}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("Qoʻshimcha", {"fields": ("email", "role")}),)
