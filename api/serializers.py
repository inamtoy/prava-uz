"""Mobil ilova uchun JSON ko'rinishlar. To'g'ri javob faqat savolga javob berilgandan keyin qaytariladi."""

from django.utils import timezone


def image_url(request, question):
    if not question.image:
        return None
    return request.build_absolute_uri(question.image.url)


def user_data(user):
    return {
        "id": user.pk,
        "username": user.username,
        "first_name": user.first_name,
        "email": user.email,
        "daily_goal": user.daily_goal,
    }


def daily_data(d):
    return {**d, "week": [{**w, "date": w["date"].isoformat()} for w in d["week"]]}


def current_data(exam):
    data = exam_summary(exam)
    data.update({
        "answered_count": exam.answered_count,
        "time_left": exam.time_left_seconds if exam.is_exam else None,
    })
    return data


def topic_data(topic, progress=0):
    return {
        "id": topic.pk,
        "slug": topic.slug,
        "name": topic.name,
        "order": topic.order,
        "question_count": getattr(topic, "question_count", None),
        "progress": progress,
    }


def answer_feedback(item, correct_answer):
    """Javob berilgan savol uchun natija: saytdagi /api/imtihon/<id>/javob/ bilan bir xil maydonlar."""
    return {
        "is_correct": item.is_correct,
        "selected_answer_id": item.selected_answer_id,
        "correct_answer_id": correct_answer.pk if correct_answer else None,
        "explanation": item.question.explanation,
    }


def item_data(request, item):
    q = item.question
    answers = list(q.answers.all())
    data = {
        "question_id": q.pk,
        "order": item.order,
        "text": q.text,
        "image": image_url(request, q),
        "answers": [{"id": a.pk, "text": a.text} for a in answers],
        "answered": item.selected_answer_id is not None,
    }
    if item.selected_answer_id is not None:
        data.update(answer_feedback(item, next((a for a in answers if a.is_correct), None)))
    return data


def exam_summary(exam):
    return {
        "id": exam.pk,
        "mode": exam.mode,
        "status": exam.status,
        "topic": exam.topic.name if exam.topic_id else None,
        "started_at": timezone.localtime(exam.started_at).isoformat(),
        "total_questions": exam.total_questions,
        "score": exam.score,
        "percent": exam.percent,
        "is_passed": exam.is_passed,
    }


def session_data(request, exam, items):
    data = exam_summary(exam)
    data.update({
        "time_left": exam.time_left_seconds if exam.is_exam else None,
        "duration_seconds": exam.duration_seconds if exam.is_exam else None,
        "items": [item_data(request, i) for i in items],
    })
    return data


def result_data(request, exam, items):
    data = exam_summary(exam)
    mistakes = []
    for item in items:
        if item.is_correct:
            continue
        answers = list(item.question.answers.all())
        correct = next((a for a in answers if a.is_correct), None)
        mistakes.append({
            "question_id": item.question_id,
            "order": item.order,
            "text": item.question.text,
            "image": image_url(request, item.question),
            "selected_answer": item.selected_answer.text if item.selected_answer_id else None,
            "correct_answer": correct.text if correct else None,
            "explanation": item.question.explanation,
        })
    data.update({
        "mistakes_count": exam.mistakes,
        "answered_count": sum(1 for i in items if i.selected_answer_id),
        "elapsed_seconds": exam.elapsed_seconds,
        "mistakes": mistakes,
    })
    return data
