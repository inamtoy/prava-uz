from datetime import timedelta

from django.contrib import admin
from django.db.models import Avg, Count, F, Q
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from config.admin_ui import PravaListMixin, tab

from .models import Exam, ExamAnswer

FINISHED = (Exam.STATUS_FINISHED, Exam.STATUS_EXPIRED)


def mmss(seconds):
    seconds = int(seconds or 0)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


class ResultFilter(admin.SimpleListFilter):
    title = "natija"
    parameter_name = "natija"

    def lookups(self, request, model_admin):
        return [("otdi", "Oʻtdi"), ("otmadi", "Oʻtmadi"), ("mashq", "Mashq (bahosiz)")]

    def queryset(self, request, queryset):
        return {
            "otdi": queryset.filter(is_passed=True),
            "otmadi": queryset.filter(is_passed=False),
            "mashq": queryset.filter(is_passed__isnull=True),
        }.get(self.value(), queryset)


@admin.register(Exam)
class ExamAdmin(PravaListMixin, ModelAdmin):
    list_display = ("user_display", "mode_badge", "score_display", "result_badge", "time_spent", "started_at")
    list_display_links = ("user_display",)
    list_filter = (("started_at", RangeDateFilter), "mode", ResultFilter, "status")
    list_filter_submit = True
    list_select_related = ("user", "topic")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")
    ordering = ("-started_at",)
    filter_params = ("natija", "mode__exact", "status__exact", "started_at_from", "started_at_to")
    list_head_title = "Imtihon natijalari"
    list_head_subtitle = "Oʻquvchilar topshirgan imtihon va mashqlar, ball va xatolar tahlili."
    fieldsets = (
        ("Imtihon", {"fields": ("user", "mode", "topic", "status")}),
        ("Natija", {"fields": ("score", "total_questions", "is_passed")}),
        ("Vaqt", {"fields": ("started_at", "finished_at", "duration_seconds")}),
    )

    def get_list_head(self, request):
        today = timezone.localdate()
        exams = Exam.objects.filter(mode=Exam.MODE_EXAM)
        graded = exams.filter(status__in=FINISHED)
        counts = Exam.objects.aggregate(
            total=Count("id"),
            passed=Count("id", filter=Q(is_passed=True)),
            failed=Count("id", filter=Q(is_passed=False)),
            practice=Count("id", filter=Q(is_passed__isnull=True)),
        )
        day = exams.aggregate(
            today=Count("id", filter=Q(started_at__date=today)),
            yesterday=Count("id", filter=Q(started_at__date=today - timedelta(days=1))),
        )
        avg = graded.aggregate(score=Avg("score"), total=Avg("total_questions"))
        rate = round(counts["passed"] * 100 / (counts["passed"] + counts["failed"]), 1) if counts["passed"] + counts["failed"] else 0
        durations = graded.filter(finished_at__isnull=False).annotate(spent=F("finished_at") - F("started_at"))
        spent = durations.aggregate(avg=Avg("spent"))["avg"]
        limit = Exam._meta.get_field("duration_seconds").default
        diff = day["today"] - day["yesterday"]
        return {
            "count_label": f"Jami {counts['total']} ta urinish",
            "kpis": [
                {"label": "Bugungi imtihonlar", "value": day["today"], "icon": "fact_check",
                 "note": f"Kecha: {day['yesterday']} ({'+' if diff >= 0 else ''}{diff})"},
                {"label": "Muvaffaqiyat koʻrsatkichi", "value": f"{rate}%", "icon": "trending_up", "tone": "accent",
                 "note": f"Oʻrtacha ball: {avg['score']:.1f} / {avg['total']:.0f}" if avg["total"] else "Hali yakunlangan imtihon yoʻq"},
                {"label": "Oʻrtacha sarflangan vaqt", "value": mmss(spent.total_seconds()) if spent else "—",
                 "unit": "daq : son" if spent else "", "icon": "timer", "note": f"Belgilangan meʼyor: {mmss(limit)} daq"},
            ],
            "tabs": [
                tab(request, "natija", None, "Barchasi", counts["total"]),
                tab(request, "natija", "otdi", "Oʻtdi", counts["passed"]),
                tab(request, "natija", "otmadi", "Oʻtmadi", counts["failed"]),
                tab(request, "natija", "mashq", "Mashq", counts["practice"]),
            ],
        }

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """Xatolar tahlili: har savol uchun tanlangan va to'g'ri javob (inline jadval o'rniga)."""
        items = []
        rows = (
            ExamAnswer.objects.filter(exam_id=object_id)
            .select_related("question__topic", "selected_answer")
            .prefetch_related("question__answers")
        )
        for item in rows:
            correct = next((a for a in item.question.answers.all() if a.is_correct), None)
            state = "empty" if item.selected_answer_id is None else "ok" if item.is_correct else "bad"
            items.append({"item": item, "correct": correct, "state": state})
        counts = {state: sum(1 for i in items if i["state"] == state) for state in ("ok", "bad", "empty")}
        exam = Exam.objects.filter(pk=object_id).first() if str(object_id).isdigit() else None
        times = {"spent": mmss(exam.elapsed_seconds), "limit": mmss(exam.duration_seconds)} if exam else {}
        extra_context = {**(extra_context or {}), "prava_items": items, "prava_counts": counts, "prava_time": times}
        return super().change_view(request, object_id, form_url, extra_context)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # faqat koʻrish

    def has_delete_permission(self, request, obj=None):
        return False  # natijalar tarixi o'chirilmaydi

    @display(description="Oʻquvchi", ordering="user__username", header=True)
    def user_display(self, obj):
        name = obj.user.get_full_name() or obj.user.username
        initials = "".join(part[:1] for part in name.split()[:2]).upper()
        return name, f"#{obj.pk} · @{obj.user.username}", initials

    @display(description="Rejim", ordering="mode")
    def mode_badge(self, obj):
        topic = format_html('<span class="prava-muted">{}</span>', obj.topic.name) if obj.topic else ""
        return format_html('<span class="prava-mode prava-mode--{}">{}</span>{}', obj.mode, obj.get_mode_display(), topic)

    @display(description="Ball va foiz", ordering="score")
    def score_display(self, obj):
        tone = "mid" if obj.is_passed is None else "ok" if obj.is_passed else "bad"
        return format_html(
            '<div class="prava-rate prava-rate--{} prava-rate--score"><strong>{} / {}</strong><span class="prava-muted">{}%</span>'
            '<div class="prava-bar"><i style="width:{}%"></i></div></div>',
            tone, obj.score, obj.total_questions, obj.percent, obj.percent,
        )

    @display(description="Vaqt")
    def time_spent(self, obj):
        if obj.status == Exam.STATUS_IN_PROGRESS:
            return format_html('<span class="prava-muted">{}</span>', "—")
        return mmss(obj.elapsed_seconds)

    @display(description="Natija", label={"Oʻtdi": "success", "Oʻtmadi": "danger", "Mashq": "info", "Jarayonda": "warning"})
    def result_badge(self, obj):
        if obj.status == Exam.STATUS_IN_PROGRESS:
            return "Jarayonda"
        if obj.is_passed is None:
            return "Mashq"
        return "Oʻtdi" if obj.is_passed else "Oʻtmadi"
