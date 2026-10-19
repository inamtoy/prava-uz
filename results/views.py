from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .models import Exam


@login_required
def result(request, pk):
    exam = get_object_or_404(Exam.objects.select_related("topic"), pk=pk, user=request.user)
    if services.expire_if_needed(exam):
        exam.refresh_from_db()
    if exam.is_in_progress:
        return redirect("exam" if exam.is_exam else "practice", pk=exam.pk)

    items = list(
        exam.items.select_related("question__topic", "selected_answer").prefetch_related("question__answers")
    )
    mistakes = [i for i in items if not i.is_correct]
    for item in mistakes:
        item.correct_answer = next((a for a in item.question.answers.all() if a.is_correct), None)
    return render(request, "results/result.html", {
        "exam": exam,
        "mistakes": mistakes,
        "answered_count": sum(1 for i in items if i.selected_answer_id),
        "unanswered_count": sum(1 for i in items if not i.selected_answer_id),
        "wrong_count": sum(1 for i in items if i.selected_answer_id and not i.is_correct),
    })
