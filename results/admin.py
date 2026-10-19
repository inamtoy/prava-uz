from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import display

from .models import Exam, ExamAnswer


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


class ExamAnswerInline(TabularInline):
    model = ExamAnswer
    extra = 0
    can_delete = False
    max_num = 0
    fields = ("order", "question_text", "selected", "correct_answer", "result")
    readonly_fields = fields
    verbose_name = "savol"
    hide_title = True
    verbose_name_plural = "Savollar va javoblar"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("question", "selected_answer")
            .prefetch_related("question__answers")
        )

    @display(description="Savol")
    def question_text(self, obj):
        return obj.question.text

    @display(description="Tanlangan javob")
    def selected(self, obj):
        return obj.selected_answer.text if obj.selected_answer else "— javob berilmagan"

    @display(description="Toʻgʻri javob")
    def correct_answer(self, obj):
        return next((a.text for a in obj.question.answers.all() if a.is_correct), "—")

    @display(description="Natija", label={"Toʻgʻri": "success", "Xato": "danger", "Javobsiz": "warning"})
    def result(self, obj):
        if obj.selected_answer_id is None:
            return "Javobsiz"
        return "Toʻgʻri" if obj.is_correct else "Xato"


@admin.register(Exam)
class ExamAdmin(ModelAdmin):
    inlines = [ExamAnswerInline]
    list_display = ("id", "user_display", "mode_badge", "topic", "score_display", "result_badge", "started_at")
    list_display_links = ("id", "user_display")
    list_filter = (("started_at", RangeDateFilter), "mode", ResultFilter, "status")
    list_filter_submit = True
    list_select_related = ("user", "topic")
    search_fields = ("user__username", "user__email", "user__first_name")
    date_hierarchy = "started_at"
    ordering = ("-started_at",)
    fieldsets = (
        ("Imtihon", {"fields": ("user", "mode", "topic", "status")}),
        ("Natija", {"fields": ("score", "total_questions", "is_passed")}),
        ("Vaqt", {"fields": ("started_at", "finished_at", "duration_seconds")}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # faqat koʻrish

    def has_delete_permission(self, request, obj=None):
        return False  # natijalar tarixi o'chirilmaydi

    @display(description="Foydalanuvchi", ordering="user__username", header=True)
    def user_display(self, obj):
        name = obj.user.get_full_name() or obj.user.username
        return name, obj.user.email, name[:1].upper()

    @display(description="Rejim", ordering="mode", label={"Imtihon": "info", "Mashq": "warning"})
    def mode_badge(self, obj):
        return obj.get_mode_display()

    @display(description="Ball", ordering="score")
    def score_display(self, obj):
        return format_html("<strong>{}</strong> / {} <span class='prava-muted'>({}%)</span>", obj.score, obj.total_questions, obj.percent)

    @display(description="Holat", label={"Oʻtdi": "success", "Oʻtmadi": "danger", "Mashq": "info", "Jarayonda": "warning"})
    def result_badge(self, obj):
        if obj.status == Exam.STATUS_IN_PROGRESS:
            return "Jarayonda"
        if obj.is_passed is None:
            return "Mashq"
        return "Oʻtdi" if obj.is_passed else "Oʻtmadi"
