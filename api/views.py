"""Mobil ilova (Flutter) uchun REST API. Mantiq results/services.py da — bu yerda faqat JSON.

Autentifikatsiya: `Authorization: Token <key>` (rest_framework.authtoken).
Begona imtihon -> 404, muddat o'tgan imtihonga javob -> 409 {expired: true}.
"""

from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from accounts.forms import RegisterForm
from quiz.models import Question, Topic
from results import services
from results.models import Exam

from . import serializers as s


def _error(message, code=status.HTTP_400_BAD_REQUEST, **extra):
    return Response({"ok": False, "error": message, **extra}, status=code)


def _items(exam):
    return list(
        exam.items.select_related("question", "selected_answer").prefetch_related("question__answers")
    )


def _token_response(user, code=status.HTTP_200_OK):
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": s.user_data(user)}, status=code)


# ---------- Hisob ----------

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def register(request):
    d = request.data
    password = d.get("password", "")
    form = RegisterForm({
        "first_name": d.get("first_name", ""),
        "username": d.get("username", ""),
        "email": d.get("email", ""),
        "password1": password,
        "password2": d.get("password2", password),
    })
    if not form.is_valid():
        errors = {k: [str(m) for m in v] for k, v in form.errors.items()}
        if "password2" in errors:
            errors.setdefault("password", []).extend(errors.pop("password2"))
        first = next(iter(errors.values()))[0]
        return _error(first, errors=errors)
    return _token_response(form.save(), status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def login(request):
    user = authenticate(request, username=request.data.get("login", ""), password=request.data.get("password", ""))
    if user is None or not user.is_active:
        return _error("Login (yoki email) yoki parol notoʻgʻri.", status.HTTP_401_UNAUTHORIZED)
    return _token_response(user)


@api_view(["POST"])
def logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response({"ok": True})


@api_view(["GET"])
def me(request):
    return Response(s.user_data(request.user))


# ---------- Ma'lumotnoma ----------

@api_view(["GET"])
@permission_classes([AllowAny])
def config(request):
    return Response({
        "exam_question_count": settings.EXAM_QUESTION_COUNT,
        "exam_duration_seconds": settings.EXAM_DURATION_SECONDS,
        "exam_max_mistakes": settings.EXAM_MAX_MISTAKES,
        "question_count": Question.objects.filter(is_active=True).count(),
    })


@api_view(["GET"])
def topics(request):
    qs = (
        Topic.objects.annotate(question_count=Count("questions", filter=Q(questions__is_active=True)))
        .filter(question_count__gt=0)
        .order_by("order", "name")
    )
    progress = services.topic_progress(request.user)
    return Response([s.topic_data(t, progress.get(t.pk, 0)) for t in qs])


# ---------- Mashq va imtihon ----------

@api_view(["POST"])
def practice_start(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    try:
        exam = services.start_practice(request.user, topic)
    except services.ExamError as e:
        return _error(str(e))
    exam = Exam.objects.select_related("topic").get(pk=exam.pk)
    return Response(s.session_data(request, exam, _items(exam)), status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def exam_current_or_start(request):
    """GET — ochiq imtihon (yoki null), POST — boshlash (ochiq bo'lsa davom ettiradi)."""
    if request.method == "GET":
        current = (
            Exam.objects.filter(user=request.user, mode=Exam.MODE_EXAM, status=Exam.STATUS_IN_PROGRESS)
            .order_by("-started_at")
            .first()
        )
        if current is not None and services.expire_if_needed(current):
            current = None
        return Response({"current": s.exam_summary(current) if current else None})

    try:
        exam = services.start_exam(request.user)
    except services.ExamError as e:
        return _error(str(e))
    data = s.session_data(request, exam, _items(exam))
    data["resumed"] = exam.resumed
    return Response(data, status=status.HTTP_200_OK if exam.resumed else status.HTTP_201_CREATED)


@api_view(["GET"])
def session(request, pk):
    exam = get_object_or_404(Exam.objects.select_related("topic"), pk=pk, user=request.user)
    if services.expire_if_needed(exam):
        exam.refresh_from_db()
    return Response(s.session_data(request, exam, _items(exam)))


@api_view(["POST"])
def answer(request, pk):
    exam = get_object_or_404(Exam, pk=pk, user=request.user)
    try:
        question_id = int(request.data["question_id"])
        answer_id = int(request.data["answer_id"])
    except (KeyError, TypeError, ValueError):
        return _error("Soʻrov notoʻgʻri.")
    try:
        item = services.save_answer(exam, question_id, answer_id, user=request.user)
    except services.ExamExpired as e:
        return _error(str(e), status.HTTP_409_CONFLICT, expired=True)
    except services.ExamError as e:
        return _error(str(e))

    correct = item.question.answers.filter(is_correct=True).first()
    data = {"ok": True, **s.answer_feedback(item, correct)}
    if exam.is_exam:
        data["time_left"] = exam.time_left_seconds
    return Response(data)


@api_view(["POST"])
def finish(request, pk):
    exam = get_object_or_404(Exam, pk=pk, user=request.user)
    exam = services.finish_exam(exam)
    exam = Exam.objects.select_related("topic").get(pk=exam.pk)
    return Response(s.result_data(request, exam, _items(exam)))


@api_view(["GET"])
def result(request, pk):
    exam = get_object_or_404(Exam.objects.select_related("topic"), pk=pk, user=request.user)
    if services.expire_if_needed(exam):
        exam.refresh_from_db()
    if exam.is_in_progress:
        return _error("Imtihon hali yakunlanmagan.", status.HTTP_409_CONFLICT)
    return Response(s.result_data(request, exam, _items(exam)))


# ---------- Statistika ----------

@api_view(["GET"])
def stats(request):
    st = services.user_stats(request.user)
    recent = (
        Exam.objects.filter(user=request.user, status__in=services.FINISHED_STATUSES)
        .select_related("topic")
        .order_by("-started_at")[:10]
    )

    def topic_row(t):
        return {"slug": t["topic"].slug, "name": t["topic"].name, "total": t["total"],
                "correct": t["correct"], "percent": t["percent"]}

    return Response({
        "total_exams": st["total_exams"],
        "passed_exams": st["passed_exams"],
        "average_percent": st["average_percent"],
        "best_percent": st["best_percent"],
        "practice_count": st["practice_count"],
        "practiced_topics": [topic_row(t) for t in st["practiced_topics"]],
        "weakest_topics": [topic_row(t) for t in st["weakest_topics"]],
        "recent_exams": [s.exam_summary(e) for e in recent],
    })
