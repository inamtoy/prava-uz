from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, Max, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from config.admin_ui import PravaListMixin, tab
from results.models import Exam

from .models import User

FINISHED = (Exam.STATUS_FINISHED, Exam.STATUS_EXPIRED)


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
class UserAdmin(PravaListMixin, BaseUserAdmin, ModelAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = ("user_display", "role_badge", "exam_count", "best_result", "last_activity", "joined", "details")
    list_display_links = ("user_display",)
    list_filter = ("role", "is_active", "date_joined")
    filter_params = ("role__exact", "is_active__exact")
    list_head_title = "Foydalanuvchilar boshqaruvi"
    list_head_subtitle = "Platformada roʻyxatdan oʻtgan barcha oʻquvchilar va administratorlar."
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
        graded = Q(exams__mode=Exam.MODE_EXAM, exams__status__in=FINISHED)
        return super().get_queryset(request).annotate(
            _exams=Count("exams", filter=graded),
            _best=Max("exams__score", filter=graded),
            _last_exam=Max("exams__started_at"),
        )

    def get_list_head(self, request):
        week_ago = timezone.now() - timedelta(days=7)
        month_ago = timezone.now() - timedelta(days=30)
        users = User.objects.aggregate(
            total=Count("id"),
            students=Count("id", filter=Q(role=User.ROLE_STUDENT)),
            admins=Count("id", filter=Q(role=User.ROLE_ADMIN)),
            month=Count("id", filter=Q(date_joined__gte=month_ago)),
        )
        graded = Exam.objects.filter(mode=Exam.MODE_EXAM, status__in=FINISHED)
        active = graded.filter(started_at__gte=week_ago).values("user").distinct().count()
        avg = graded.aggregate(score=Avg("score"), total=Avg("total_questions"))
        readiness = round(avg["score"] * 100 / avg["total"], 1) if avg["total"] else 0
        target = round((settings.EXAM_QUESTION_COUNT - settings.EXAM_MAX_MISTAKES) * 100 / settings.EXAM_QUESTION_COUNT)
        return {
            "count_label": f"{users['total']} ta jami",
            "actions": [{"label": "Yangi foydalanuvchi", "icon": "person_add", "style": "accent",
                         "url": reverse("admin:accounts_user_add")}],
            "kpis": [
                {"label": "Jami foydalanuvchilar", "value": users["total"], "unit": "ta", "icon": "group", "tone": "ink",
                 "note": f"Oxirgi 30 kunda +{users['month']} ta"},
                {"label": "Faol oʻrganuvchilar", "value": active, "unit": "ta", "icon": "bolt", "tone": "accent",
                 "note": "Oxirgi 7 kunda imtihon topshirgan"},
                {"label": "Oʻrtacha tayyorgarlik", "value": f"{readiness}%", "icon": "speed",
                 "bar": min(readiness, 100), "note": f"Maqsad: {target}% (imtihondan oʻtish)"},
            ],
            "tabs": [
                tab(request, "role__exact", None, "Barchasi", users["total"]),
                tab(request, "role__exact", User.ROLE_STUDENT, "Oʻquvchilar", users["students"]),
                tab(request, "role__exact", User.ROLE_ADMIN, "Adminlar", users["admins"]),
            ],
        }

    @display(description="Foydalanuvchi", ordering="username", header=True)
    def user_display(self, obj):
        name = obj.get_full_name() or obj.username
        initials = "".join(part[:1] for part in name.split()[:2]).upper()
        return name, f"@{obj.username} · {obj.email}" if obj.email else f"@{obj.username}", initials

    @display(description="Rol", ordering="role", label={"Admin": "warning", "Oʻquvchi": "info"})
    def role_badge(self, obj):
        return obj.get_role_display()

    @display(description="Imtihonlar", ordering="_exams")
    def exam_count(self, obj):
        return f"{obj._exams} ta"

    @display(description="Eng yaxshi natija", ordering="_best")
    def best_result(self, obj):
        if obj._best is None:
            return format_html('<span class="prava-muted">{}</span>', "—")
        total = settings.EXAM_QUESTION_COUNT
        passed = obj._best >= total - settings.EXAM_MAX_MISTAKES
        return format_html(
            '<span class="prava-score prava-score--{}"><span class="material-symbols-outlined">{}</span>{} / {} ({}%)</span>',
            "ok" if passed else "muted", "check_circle" if passed else "schedule", obj._best, total, round(obj._best * 100 / total),
        )

    @display(description="Oxirgi faollik", ordering="_last_exam")
    def last_activity(self, obj):
        moment = max(filter(None, [obj._last_exam, obj.last_login]), default=None)
        if moment is None:
            return format_html('<span class="prava-muted">{}</span>', "Hali kirmagan")
        recent = timezone.now() - moment < timedelta(days=1)
        return format_html('<span class="prava-when{}">{}</span>', " is-recent" if recent else "",
                           timezone.localtime(moment).strftime("%d.%m.%Y, %H:%M"))

    @display(description="Roʻyxatdan oʻtgan", ordering="date_joined")
    def joined(self, obj):
        return timezone.localtime(obj.date_joined).strftime("%d.%m.%Y")

    @display(description="")
    def details(self, obj):
        return format_html('<a class="prava-link prava-link--chip" href="{}">{}</a>',
                           reverse("admin:accounts_user_change", args=[obj.pk]), "Batafsil")
