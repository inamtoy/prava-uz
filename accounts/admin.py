from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import User


class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name", "role")


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


# Guruhlar unfold ko'rinishida (rollar asosan `role` maydoni orqali boshqariladi)
admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ("user_display", "role_badge", "exam_count", "is_active", "date_joined", "last_login")
    list_display_links = ("user_display",)
    list_filter = ("role", "is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("is_staff", "is_superuser", "last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Shaxsiy maʼlumotlar", {"fields": ("first_name", "last_name", "email")}),
        ("Rol va ruxsatlar", {
            "fields": ("role", "is_active", "is_staff", "is_superuser"),
            "description": "Admin roli boshqaruv paneliga toʻliq kirish huquqini beradi; "
                           "«is_staff» va «is_superuser» roldan avtomatik belgilanadi.",
        }),
        ("Muhim sanalar", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_exams=Count("exams"))

    @display(description="Foydalanuvchi", ordering="username", header=True)
    def user_display(self, obj):
        name = obj.get_full_name() or obj.username
        return name, obj.email, name[:1].upper()

    @display(description="Rol", ordering="role", label={"Admin": "danger", "Oʻquvchi": "info"})
    def role_badge(self, obj):
        return obj.get_role_display()

    @display(description="Imtihonlar", ordering="_exams")
    def exam_count(self, obj):
        return obj._exams
