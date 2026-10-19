from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from results import services
from results.models import Exam

from .forms import LoginForm, RegisterForm

ADMIN_ONLY_MESSAGE = "Bu boʻlimga faqat administratorlar kira oladi."


def _is_admin_path(url):
    return url.startswith(reverse("admin:index"))


def safe_next(request, url):
    """`next` faqat shu saytga tegishli bo'lsa qaytariladi, aks holda bo'sh satr."""
    if url and url_has_allowed_host_and_scheme(url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return url
    return ""


def redirect_url_for(user, next_url=""):
    """Kirishdan keyingi manzil: rolga ruxsat etilgan `next`, aks holda admin -> panel, o'quvchi -> profil."""
    if next_url and (user.is_admin_role or not _is_admin_path(next_url)):
        return next_url
    return reverse("admin:index") if user.is_admin_role else reverse("profile")


class RoleLoginView(auth_views.LoginView):
    """Yagona kirish sahifasi (o'quvchi va admin uchun)."""

    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return redirect_url_for(self.request.user, self.get_redirect_url())


def admin_login_redirect(request):
    """Django admin'ning o'z login sahifasi o'rniga — yagona login'ga (next saqlanadi)."""
    next_url = safe_next(request, request.GET.get(REDIRECT_FIELD_NAME, "")) or reverse("admin:index")
    if request.user.is_authenticated:
        if request.user.is_admin_role:
            return redirect(next_url)
        messages.warning(request, ADMIN_ONLY_MESSAGE)
        return redirect("profile")
    return redirect(f"{reverse('login')}?{urlencode({REDIRECT_FIELD_NAME: next_url})}")


def register(request):
    if request.user.is_authenticated:
        return redirect(redirect_url_for(request.user))
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="accounts.backends.EmailOrUsernameBackend")
        messages.success(request, f"Xush kelibsiz, {user.first_name or user.username}! Endi mavzuni tanlab mashq qilishingiz mumkin.")
        return redirect("topic_list")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    finished = Exam.objects.filter(user=request.user, status__in=services.FINISHED_STATUSES).select_related("topic")
    recent = list(finished.order_by("-started_at")[:10])
    chart_exams = list(finished.filter(mode=Exam.MODE_EXAM).order_by("-started_at")[:10])[::-1]
    return render(request, "accounts/profile.html", {
        "stats": services.user_stats(request.user),
        "recent_exams": recent,
        "chart_data": {
            "labels": [timezone.localtime(e.started_at).strftime("%d.%m") for e in chart_exams],
            "percents": [e.percent for e in chart_exams],
        },
        "open_exam": Exam.objects.filter(
            user=request.user, mode=Exam.MODE_EXAM, status=Exam.STATUS_IN_PROGRESS
        ).first(),
    })

