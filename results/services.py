"""Imtihon va mashq mantiqi. View'lar faqat shu funksiyalarni chaqiradi."""

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.utils import timezone

from quiz.models import Answer, Question, Topic

from .models import Exam, ExamAnswer

FINISHED_STATUSES = (Exam.STATUS_FINISHED, Exam.STATUS_EXPIRED)


class ExamError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato (matni o'zbekcha)."""


class ExamExpired(ExamError):
    pass


def _create_session(user, mode, questions, topic=None):
    if not questions:
        raise ExamError("Hozircha savollar mavjud emas.")
    exam = Exam.objects.create(
        user=user,
        mode=mode,
        topic=topic,
        total_questions=len(questions),
        duration_seconds=settings.EXAM_DURATION_SECONDS,
    )
    ExamAnswer.objects.bulk_create([
        ExamAnswer(exam=exam, question=q, order=i) for i, q in enumerate(questions, start=1)
    ])
    return exam


@transaction.atomic
def start_exam(user):
    """Ochiq imtihon bo'lsa — uni qaytaradi (exam.resumed=True), aks holda yangisini yaratadi."""
    current = (
        Exam.objects.filter(user=user, mode=Exam.MODE_EXAM, status=Exam.STATUS_IN_PROGRESS)
        .order_by("-started_at")
        .first()
    )
    if current is not None:
        if not expire_if_needed(current):
            current.resumed = True
            return current

    questions = list(
        Question.objects.filter(is_active=True).order_by("?")[: settings.EXAM_QUESTION_COUNT]
    )
    exam = _create_session(user, Exam.MODE_EXAM, questions)
    exam.resumed = False
    return exam


@transaction.atomic
def start_practice(user, topic):
    questions = list(
        topic.questions.filter(is_active=True).order_by("?")[: settings.PRACTICE_QUESTION_COUNT]
    )
    if not questions:
        raise ExamError("Bu mavzuda hozircha savollar yoʻq.")
    return _create_session(user, Exam.MODE_PRACTICE, questions, topic=topic)


def expire_if_needed(exam):
    """Muddat o'tgan ochiq imtihonni yakunlaydi. Yakunlangan bo'lsa True qaytaradi."""
    if exam.is_in_progress and exam.is_expired:
        finish_exam(exam)
        return True
    return False


def save_answer(exam, question_id, answer_id, user=None):
    if user is not None and exam.user_id != user.pk:
        raise Http404
    if not exam.is_in_progress:
        raise ExamError("Bu imtihon allaqachon yakunlangan.")
    # Muddat tekshiruvi transaksiyadan tashqarida: xato ko'tarilganda ham imtihon yopilib qoladi.
    if expire_if_needed(exam):
        raise ExamExpired("Imtihon vaqti tugadi. Javob qabul qilinmadi.")

    with transaction.atomic():
        try:
            item = ExamAnswer.objects.select_for_update().get(exam=exam, question_id=question_id)
        except (ExamAnswer.DoesNotExist, ValueError, TypeError):
            raise ExamError("Bu savol ushbu imtihonga tegishli emas.")
        try:
            answer = Answer.objects.get(pk=answer_id, question_id=item.question_id)
        except (Answer.DoesNotExist, ValueError, TypeError):
            raise ExamError("Bu javob ushbu savolga tegishli emas.")

        # Birinchi javob hisoblanadi — to'g'ri/xato darrov ko'rsatiladi, keyin o'zgartirib bo'lmaydi.
        if item.selected_answer_id is not None:
            return item

        item.selected_answer = answer
        item.is_correct = answer.is_correct  # faqat serverdagi qiymat
        item.answered_at = timezone.now()
        item.save(update_fields=["selected_answer", "is_correct", "answered_at"])
        return item


@transaction.atomic
def finish_exam(exam):
    exam = Exam.objects.select_for_update().get(pk=exam.pk)
    if not exam.is_in_progress:
        return exam
    now = timezone.now()
    exam.score = exam.items.filter(is_correct=True).count()
    if exam.is_exam:
        # Javob berilmagan savol is_correct=False — ya'ni xato hisoblanadi.
        exam.is_passed = exam.mistakes <= settings.EXAM_MAX_MISTAKES
        exam.status = Exam.STATUS_EXPIRED if now > exam.deadline else Exam.STATUS_FINISHED
        exam.finished_at = min(now, exam.deadline)
    else:
        exam.is_passed = None
        exam.status = Exam.STATUS_FINISHED
        exam.finished_at = now
    exam.save(update_fields=["score", "is_passed", "status", "finished_at"])
    return exam


def user_stats(user):
    finished = Exam.objects.filter(user=user, status__in=FINISHED_STATUSES)
    exams = list(finished.filter(mode=Exam.MODE_EXAM).only("score", "total_questions", "is_passed"))
    percents = [e.percent for e in exams]

    rows = (
        ExamAnswer.objects.filter(exam__in=finished)
        .values("question__topic_id")
        .annotate(total=Count("id"), correct=Count("id", filter=Q(is_correct=True)))
    )
    by_topic = {r["question__topic_id"]: r for r in rows}
    topics = []
    for topic in Topic.objects.all():
        r = by_topic.get(topic.pk)
        total = r["total"] if r else 0
        correct = r["correct"] if r else 0
        topics.append({
            "topic": topic,
            "total": total,
            "correct": correct,
            "percent": round(correct * 100 / total) if total else 0,
        })
    attempted = [t for t in topics if t["total"]]
    weakest = sorted(attempted, key=lambda t: (t["percent"], -t["total"]))[:3]

    return {
        "total_exams": len(exams),
        "passed_exams": sum(1 for e in exams if e.is_passed),
        "average_percent": round(sum(percents) / len(percents)) if percents else 0,
        "best_percent": max(percents) if percents else 0,
        "practice_count": finished.filter(mode=Exam.MODE_PRACTICE).count(),
        "topics": topics,
        "weakest_topics": weakest,
    }


def topic_progress(user):
    """{topic_id: %} — mavzudagi faol savollardan kamida bir marta to'g'ri yechilganlari ulushi."""
    solved = (
        ExamAnswer.objects.filter(exam__user=user, is_correct=True, question__is_active=True)
        .values("question__topic_id")
        .annotate(n=Count("question_id", distinct=True))
    )
    solved = {r["question__topic_id"]: r["n"] for r in solved}
    totals = Topic.objects.annotate(n=Count("questions", filter=Q(questions__is_active=True))).values("id", "n")
    return {t["id"]: round(solved.get(t["id"], 0) * 100 / t["n"]) if t["n"] else 0 for t in totals}
