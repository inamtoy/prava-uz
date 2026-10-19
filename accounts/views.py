from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from results import services
from results.models import Exam

from .forms import RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect("topic_list")
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

