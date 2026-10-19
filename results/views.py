from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .models import Exam


@login_required
def result(request, pk):
    exam = get_object_or_404(Exam.objects.select_related("topic"), pk=pk, user=request.user)
    services.expire_if_needed(exam)
    if exam.is_in_progress:
        return redirect("practice" if not exam.is_exam else "exam", pk=exam.pk)
    exam.refresh_from_db()
    return render(request, "results/result.html", {"exam": exam})
