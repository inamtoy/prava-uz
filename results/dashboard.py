"""Admin bosh sahifasi (unfold DASHBOARD_CALLBACK) — hammasi bazadagi real ma'lumotdan, har blok bitta so'rov."""

import json
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, ExpressionWrapper, F, FloatField, Q
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from quiz.models import Question, Topic

from .models import Exam, ExamAnswer

FINISHED = (Exam.STATUS_FINISHED, Exam.STATUS_EXPIRED)
WEEKDAYS = ["Dush", "Sesh", "Chor", "Pay", "Juma", "Shan", "Yak"]
MONTHS = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust",
          "sentabr", "oktabr", "noyabr", "dekabr"]
WEEKDAYS_FULL = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]
MIN_TOPIC_QUESTIONS = 15


def _greeting(hour):
    if 5 <= hour < 11:
        return "Xayrli tong"
    if 11 <= hour < 17:
        return "Xayrli kun"
    if 17 <= hour < 22:
        return "Xayrli kech"
    return "Xayrli tun"


def _percent(part, whole):
    return round(part * 100 / whole) if whole else 0


def _kpis(today):
    questions = Question.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        week=Count("id", filter=Q(created_at__date__gte=today - timedelta(days=6))),
    )
    users = User.objects.aggregate(
        students=Count("id", filter=Q(role=User.ROLE_STUDENT)),
        week=Count("id", filter=Q(role=User.ROLE_STUDENT, date_joined__date__gte=today - timedelta(days=6))),
    )
    exams = Exam.objects.filter(mode=Exam.MODE_EXAM).aggregate(
        today=Count("id", filter=Q(started_at__date=today)),
        yesterday=Count("id", filter=Q(started_at__date=today - timedelta(days=1))),
        finished=Count("id", filter=Q(status__in=FINISHED)),
        passed=Count("id", filter=Q(status__in=FINISHED, is_passed=True)),
    )
    return {
        "questions": questions,
        "users": users,
        "exams": exams,
        "pass_rate": _percent(exams["passed"], exams["finished"]),
        "min_correct": settings.EXAM_QUESTION_COUNT - settings.EXAM_MAX_MISTAKES,
    }


def _week_chart(today):
    start = today - timedelta(days=6)
    rows = (
        Exam.objects.filter(mode=Exam.MODE_EXAM, status__in=FINISHED, started_at__date__gte=start)
        .annotate(day=TruncDate("started_at"))
        .values("day")
        .annotate(total=Count("id"), passed=Count("id", filter=Q(is_passed=True)))
    )
    by_day = {r["day"]: r for r in rows}
    days = [start + timedelta(days=i) for i in range(7)]
    totals = [by_day.get(d, {}).get("total", 0) for d in days]
    passed = [by_day.get(d, {}).get("passed", 0) for d in days]
    data = {
        "labels": [f"{WEEKDAYS[d.weekday()]} {d.day:02d}.{d.month:02d}" for d in days],
        "datasets": [
            {"label": "Topshirildi", "data": totals, "borderColor": "#0B1B33",
             "backgroundColor": "rgba(11, 27, 51, .08)", "fill": True, "tension": 0.2, "pointRadius": 4},
            {"label": "Oʻtdi", "data": passed, "borderColor": "#FFC220",
             "backgroundColor": "rgba(255, 194, 32, .18)", "fill": True, "tension": 0.2, "pointRadius": 4},
        ],
    }
    total = sum(totals)
    return {
        "json": json.dumps(data),
        "total": total,
        "passed": sum(passed),
        "daily_avg": round(total / 7, 1),
    }


def _topic_stats():
    rows = (
        ExamAnswer.objects.filter(exam__status__in=FINISHED, selected_answer__isnull=False)
        .values("question__topic_id")
        .annotate(total=Count("id"), correct=Count("id", filter=Q(is_correct=True)))
    )
    by_topic = {r["question__topic_id"]: r for r in rows}
    items = []
    for topic in Topic.objects.annotate(active=Count("questions", filter=Q(questions__is_active=True))).order_by("order", "name"):
        r = by_topic.get(topic.pk, {"total": 0, "correct": 0})
        percent = _percent(r["correct"], r["total"])
        items.append({
            "topic": topic,
            "active": topic.active,
            "total": r["total"],
            "percent": percent,
            "tone": "none" if not r["total"] else "bad" if percent < 60 else "mid" if percent < 80 else "ok",
        })
    return items


def _hardest_questions(limit=5):
    rows = (
        ExamAnswer.objects.filter(exam__status__in=FINISHED, selected_answer__isnull=False)
        .values("question_id", "question__text", "question__topic__name")
        .annotate(total=Count("id"), wrong=Count("id", filter=Q(is_correct=False)))
        .filter(wrong__gt=0)
        .annotate(rate=ExpressionWrapper(F("wrong") * 100.0 / F("total"), output_field=FloatField()))
        .order_by("-rate", "-wrong")[:limit]
    )
    return [
        {
            "id": r["question_id"],
            "text": r["question__text"],
            "topic": r["question__topic__name"],
            "total": r["total"],
            "wrong": r["wrong"],
            "rate": round(r["rate"]),
            "url": reverse("admin:quiz_question_change", args=[r["question_id"]]),
        }
        for r in rows
    ]


def _recent_exams(limit=6):
    return list(
        Exam.objects.filter(status__in=FINISHED)
        .select_related("user", "topic")
        .order_by("-finished_at")[:limit]
    )


def _content_health(topic_stats):
    changelist = reverse("admin:quiz_question_changelist")
    no_explanation = Question.objects.filter(is_active=True, explanation="").count()
    small_topics = [t for t in topic_stats if t["active"] < MIN_TOPIC_QUESTIONS]
    inactive = Question.objects.filter(is_active=False).count()
    alerts = []
    if no_explanation:
        alerts.append({
            "tone": "warn", "icon": "warning",
            "title": f"{no_explanation} ta savolda izoh yoʻq",
            "text": "Oʻquvchi xatosini tushunishi uchun izoh qoʻshing.",
            "link": f"{changelist}?izoh=yoq&is_active__exact=1", "link_text": "Izoh kiritish",
        })
    for t in small_topics[:3]:
        alerts.append({
            "tone": "info", "icon": "bolt",
            "title": f"«{t['topic'].name}» mavzusida {t['active']} ta savol",
            "text": f"Har bir mavzuda kamida {MIN_TOPIC_QUESTIONS} ta faol savol boʻlishi tavsiya etiladi.",
            "link": reverse("admin:quiz_question_add") + f"?topic={t['topic'].pk}", "link_text": "Savol qoʻshish",
        })
    if len(small_topics) > 3:
        alerts.append({
            "tone": "info", "icon": "more_horiz",
            "title": f"Yana {len(small_topics) - 3} ta mavzuda savollar kam",
            "text": f"{MIN_TOPIC_QUESTIONS} tadan kam faol savolli mavzular.",
            "link": reverse("admin:quiz_topic_changelist"), "link_text": "Mavzularni koʻrish",
        })
    if inactive:
        alerts.append({
            "tone": "muted", "icon": "pause_circle",
            "title": f"{inactive} ta savol nofaol",
            "text": "Nofaol savollar imtihon va mashqda chiqmaydi.",
            "link": f"{changelist}?is_active__exact=0", "link_text": "Koʻrib chiqish",
        })
    if not alerts:
        alerts.append({
            "tone": "ok", "icon": "verified",
            "title": "Kontent tartibda",
            "text": "Barcha faol savollarda izoh bor va mavzular yetarli toʻldirilgan.",
            "link": "", "link_text": "",
        })
    return {"alerts": alerts, "issues": sum(1 for a in alerts if a["tone"] in ("warn", "info"))}


def dashboard_callback(request, context):
    now = timezone.localtime()
    today = now.date()
    topic_stats = _topic_stats()
    context.update({
        "dash": {
            "greeting": _greeting(now.hour),
            "name": request.user.first_name or request.user.username,
            "date": f"{today.day}-{MONTHS[today.month - 1]}, {today.year}-yil · {WEEKDAYS_FULL[today.weekday()]}",
            "kpi": _kpis(today),
            "chart": _week_chart(today),
            "topics": topic_stats,
            "hardest": _hardest_questions(),
            "recent": _recent_exams(),
            "health": _content_health(topic_stats),
            "links": {
                "add_question": reverse("admin:quiz_question_add"),
                "questions": reverse("admin:quiz_question_changelist"),
                "exams": reverse("admin:results_exam_changelist"),
            },
        },
    })
    return context
