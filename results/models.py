from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Exam(models.Model):
    MODE_EXAM = "exam"
    MODE_PRACTICE = "practice"
    MODE_CHOICES = [(MODE_EXAM, "Imtihon"), (MODE_PRACTICE, "Mashq")]

    STATUS_IN_PROGRESS = "in_progress"
    STATUS_FINISHED = "finished"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "Jarayonda"),
        (STATUS_FINISHED, "Yakunlangan"),
        (STATUS_EXPIRED, "Vaqt tugagan"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exams", verbose_name="foydalanuvchi")
    mode = models.CharField("rejim", max_length=20, choices=MODE_CHOICES, default=MODE_EXAM)
    topic = models.ForeignKey("quiz.Topic", on_delete=models.SET_NULL, null=True, blank=True, related_name="exams", verbose_name="mavzu")
    started_at = models.DateTimeField("boshlangan", auto_now_add=True)
    finished_at = models.DateTimeField("yakunlangan", null=True, blank=True)
    duration_seconds = models.PositiveIntegerField("davomiyligi (s)", default=1500)
    total_questions = models.PositiveSmallIntegerField("savollar soni", default=0)
    score = models.PositiveSmallIntegerField("toʻgʻri javoblar", default=0)
    is_passed = models.BooleanField("oʻtdi", null=True, blank=True)
    status = models.CharField("holat", max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS)

    class Meta:
        db_table = "imtihonlar"
        ordering = ["-started_at"]
        verbose_name = "imtihon"
        verbose_name_plural = "imtihonlar"

    def __str__(self):
        return f"#{self.pk} {self.user} — {self.get_mode_display()}"

    @property
    def is_exam(self):
        return self.mode == self.MODE_EXAM

    @property
    def is_in_progress(self):
        return self.status == self.STATUS_IN_PROGRESS

    @property
    def deadline(self):
        return self.started_at + timedelta(seconds=self.duration_seconds)

    @property
    def time_left_seconds(self):
        if not self.is_exam:
            return None
        return max(0, int((self.deadline - timezone.now()).total_seconds()))

    @property
    def is_expired(self):
        return self.is_exam and timezone.now() > self.deadline

    @property
    def percent(self):
        if not self.total_questions:
            return 0
        return round(self.score * 100 / self.total_questions)

    @property
    def mistakes(self):
        return self.total_questions - self.score

    @property
    def elapsed_seconds(self):
        end = self.finished_at or timezone.now()
        seconds = int((end - self.started_at).total_seconds())
        if self.is_exam:
            seconds = min(seconds, self.duration_seconds)
        return max(0, seconds)


class ExamAnswer(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="items", verbose_name="imtihon")
    question = models.ForeignKey("quiz.Question", on_delete=models.CASCADE, related_name="exam_answers", verbose_name="savol")
    selected_answer = models.ForeignKey("quiz.Answer", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", verbose_name="tanlangan javob")
    is_correct = models.BooleanField("toʻgʻri", default=False)
    order = models.PositiveSmallIntegerField("tartib", default=0)
    answered_at = models.DateTimeField("javob vaqti", null=True, blank=True)

    class Meta:
        db_table = "imtihon_javoblari"
        ordering = ["order"]
        unique_together = ("exam", "question")
        verbose_name = "imtihon javobi"
        verbose_name_plural = "imtihon javoblari"

    def __str__(self):
        return f"{self.exam_id} / {self.order}"
