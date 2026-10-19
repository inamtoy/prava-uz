import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from results import services
from results.models import Exam

from .models import Question, Topic


def home(request):
    return render(request, "quiz/home.html")


@login_required
def topic_list(request):
    topics = Topic.objects.annotate(
        question_count=Count("questions", filter=Q(questions__is_active=True))
    ).order_by("order", "name")
    progress = services.topic_progress(request.user)
    for topic in topics:
        topic.progress = progress.get(topic.pk, 0)
    return render(request, "quiz/topic_list.html", {"topics": topics})


@login_required
@require_POST
def practice_start(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    try:
        exam = services.start_practice(request.user, topic)
    except services.ExamError as e:
        messages.warning(request, str(e))
        return redirect("topic_list")
    return redirect("practice", pk=exam.pk)


def _session_items(exam):
    return exam.items.select_related("question").prefetch_related("question__answers")


@login_required
def practice(request, pk):
    exam = get_object_or_404(Exam.objects.select_related("topic"), pk=pk, user=request.user, mode=Exam.MODE_PRACTICE)
    if not exam.is_in_progress:
        return redirect("result", pk=exam.pk)
    items = list(_session_items(exam))
    answered = sum(1 for i in items if i.selected_answer_id)
    return render(request, "quiz/practice.html", {
        "exam": exam,
        "items": items,
        "answered_count": answered,
        "correct_count": sum(1 for i in items if i.is_correct),
        "start_index": next((n for n, i in enumerate(items) if not i.selected_answer_id), 0),
    })


@login_required
@require_POST
def exam_answer(request, pk):
    exam = get_object_or_404(Exam, pk=pk, user=request.user)
    try:
        payload = json.loads(request.body or b"{}")
        question_id = int(payload["question_id"])
        answer_id = int(payload["answer_id"])
    except (ValueError, KeyError, TypeError):
        return JsonResponse({"ok": False, "error": "So'rov noto'g'ri."}, status=400)

    try:
        item = services.save_answer(exam, question_id, answer_id, user=request.user)
    except services.ExamExpired as e:
        return JsonResponse(
            {"ok": False, "expired": True, "error": str(e), "redirect": reverse("result", args=[exam.pk])},
            status=409,
        )
    except services.ExamError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

    if exam.is_exam:
        return JsonResponse({"ok": True, "time_left": exam.time_left_seconds})
    correct = item.question.answers.get(is_correct=True)
    return JsonResponse({
        "ok": True,
        "is_correct": item.is_correct,
        "selected_answer_id": item.selected_answer_id,
        "correct_answer_id": correct.pk,
        "explanation": item.question.explanation,
    })


@login_required
@require_POST
def exam_finish(request, pk):
    exam = get_object_or_404(Exam, pk=pk, user=request.user)
    exam = services.finish_exam(exam)
    return redirect("result", pk=exam.pk)


@login_required
def exam_start(request):
    if request.method == "POST":
        try:
            exam = services.start_exam(request.user)
        except services.ExamError as e:
            messages.warning(request, str(e))
            return redirect("exam_start")
        if exam.resumed:
            messages.info(request, "Sizda tugallanmagan imtihon bor — davom ettiryapsiz.")
        elif exam.total_questions < settings.EXAM_QUESTION_COUNT:
            messages.warning(
                request,
                f"Bazada savollar yetarli emas: imtihonda {exam.total_questions} ta savol bo'ladi.",
            )
        return redirect("exam", pk=exam.pk)

    current = (
        Exam.objects.filter(user=request.user, mode=Exam.MODE_EXAM, status=Exam.STATUS_IN_PROGRESS)
        .order_by("-started_at")
        .first()
    )
    if current is not None and services.expire_if_needed(current):
        current = None
    return render(request, "quiz/exam_start.html", {
        "current": current,
        "question_count": settings.EXAM_QUESTION_COUNT,
        "minutes": settings.EXAM_DURATION_SECONDS // 60,
        "max_mistakes": settings.EXAM_MAX_MISTAKES,
        "min_correct": settings.EXAM_QUESTION_COUNT - settings.EXAM_MAX_MISTAKES,
        "available": Question.objects.filter(is_active=True).count(),
    })


@login_required
def exam(request, pk):
    exam = get_object_or_404(Exam, pk=pk, user=request.user, mode=Exam.MODE_EXAM)
    if services.expire_if_needed(exam):
        messages.warning(request, "Imtihon vaqti tugadi. Natijangiz quyida.")
        return redirect("result", pk=exam.pk)
    if not exam.is_in_progress:
        return redirect("result", pk=exam.pk)
    items = list(_session_items(exam))
    return render(request, "quiz/exam.html", {
        "exam": exam,
        "items": items,
        "time_left": exam.time_left_seconds,
        "start_index": next((n for n, i in enumerate(items) if not i.selected_answer_id), 0),
    })
