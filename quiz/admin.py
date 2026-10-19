from django.contrib import admin, messages
from django.db.models import Count, Q
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import RelatedDropdownFilter
from unfold.decorators import action, display

from results.models import Exam, ExamAnswer

from .forms import AnswerInlineFormSet
from .models import Answer, Question, Topic

FINISHED = (Exam.STATUS_FINISHED, Exam.STATUS_EXPIRED)
SIDE = "prava-side"  # change_form.html bu fieldset'larni o'ng ustunga chiqaradi


class AnswerInline(TabularInline):
    model = Answer
    formset = AnswerInlineFormSet
    extra = 4
    max_num = 4
    min_num = 0
    fields = ("text", "is_correct")
    hide_title = True
    verbose_name = "javob varianti"
    verbose_name_plural = "Javob variantlari"


class HasImageFilter(admin.SimpleListFilter):
    title = "rasm"
    parameter_name = "rasm"

    def lookups(self, request, model_admin):
        return [("bor", "Rasmli"), ("yoq", "Rasmsiz")]

    def queryset(self, request, queryset):
        no_image = Q(image="") | Q(image__isnull=True)
        if self.value() == "bor":
            return queryset.exclude(no_image)
        if self.value() == "yoq":
            return queryset.filter(no_image)
        return queryset


class ExplanationFilter(admin.SimpleListFilter):
    title = "izoh"
    parameter_name = "izoh"

    def lookups(self, request, model_admin):
        return [("bor", "Izohli"), ("yoq", "Izohsiz")]

    def queryset(self, request, queryset):
        if self.value() == "bor":
            return queryset.exclude(explanation="")
        if self.value() == "yoq":
            return queryset.filter(explanation="")
        return queryset


@admin.register(Topic)
class TopicAdmin(ModelAdmin):
    list_display = ("name", "order", "question_count", "active_count")
    list_display_links = ("name",)
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "order")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _question_count=Count("questions"),
            _active_count=Count("questions", filter=Q(questions__is_active=True)),
        )

    @display(description="Savollar", ordering="_question_count")
    def question_count(self, obj):
        return obj._question_count

    @display(description="Faol savollar", ordering="_active_count", label=True)
    def active_count(self, obj):
        return obj._active_count


@admin.register(Question)
class QuestionAdmin(ModelAdmin):
    inlines = [AnswerInline]
    list_display = ("thumbnail", "short_text", "topic_badge", "answer_count", "correct_rate", "is_active")
    list_display_links = ("thumbnail", "short_text")
    list_filter = (("topic", RelatedDropdownFilter), "is_active", HasImageFilter, ExplanationFilter)
    list_filter_submit = True
    list_select_related = ("topic",)
    list_per_page = 25
    search_fields = ("text", "explanation")
    actions = ["activate", "deactivate"]
    readonly_fields = ("question_stats", "created_at")
    compressed_fields = False  # Stitch: yorliq maydon ustida (o'ng ustun tor)
    fieldsets = (
        ("Savol matni", {"fields": ("text",)}),
        ("Savol izohi", {
            "fields": ("explanation",),
            "description": "Xato qilgan oʻquvchiga natija sahifasida koʻrsatiladi.",
        }),
        ("Nashr parametrlari", {"fields": ("is_active", "created_at"), "classes": [SIDE]}),
        ("Mavzu", {"fields": ("topic",), "classes": [SIDE]}),
        ("Savol rasmi", {"fields": ("image",), "classes": [SIDE]}),
        ("Savol statistikasi", {"fields": ("question_stats",), "classes": [SIDE, "prava-stats"]}),
    )

    def get_queryset(self, request):
        answered = Q(exam_answers__selected_answer__isnull=False, exam_answers__exam__status__in=FINISHED)
        return super().get_queryset(request).annotate(
            _answers=Count("answers", distinct=True),
            _answered=Count("exam_answers", filter=answered, distinct=True),
            _correct=Count("exam_answers", filter=answered & Q(exam_answers__is_correct=True), distinct=True),
        )

    def get_fieldsets(self, request, obj=None):
        if obj is None:  # yangi savolda statistika yo'q
            return [fs for fs in self.fieldsets if fs[0] != "Savol statistikasi"]
        return self.fieldsets

    @display(description="Rasm")
    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" alt="" class="prava-thumb">', obj.image.url)
        return format_html('<span class="prava-thumb prava-thumb--empty material-symbols-outlined">{}</span>', "hide_image")

    @display(description="Savol mazmuni", ordering="text")
    def short_text(self, obj):
        text = obj.text if len(obj.text) <= 90 else obj.text[:88] + "…"
        badge = "" if obj.explanation else format_html(' <span class="prava-badge prava-badge--warn">{}</span>', "Izohsiz")
        return format_html('<span class="prava-qtext">{}</span>{}<div class="prava-muted">ID: #{}</div>', text, badge, obj.pk)

    @display(description="Mavzu", ordering="topic__order", label=True)
    def topic_badge(self, obj):
        return obj.topic.name

    @display(description="Variantlar", ordering="_answers")
    def answer_count(self, obj):
        return f"{obj._answers} ta javob"

    @display(description="Toʻgʻri javob %", ordering="_correct")
    def correct_rate(self, obj):
        if not obj._answered:
            return format_html('<span class="prava-muted">{}</span>', "Hali javob yoʻq")
        percent = round(obj._correct * 100 / obj._answered)
        tone = "bad" if percent < 50 else "mid" if percent < 80 else "ok"
        return format_html(
            '<div class="prava-rate prava-rate--{}"><strong>{}%</strong><span class="prava-muted">{} ta javob</span>'
            '<div class="prava-bar"><i style="width:{}%"></i></div></div>',
            tone, percent, obj._answered, percent,
        )

    @display(description="Statistika")
    def question_stats(self, obj):
        # unfold readonly maydonni bir necha marta chaqiradi — so'rov natijasini obyektda saqlaymiz
        if not hasattr(obj, "_prava_stats"):
            obj._prava_stats = list(
                ExamAnswer.objects.filter(question=obj, exam__status__in=FINISHED, selected_answer__isnull=False)
                .values("selected_answer__text", "is_correct")
                .annotate(n=Count("id"))
                .order_by("-n")
            )
        rows = obj._prava_stats
        answered = sum(r["n"] for r in rows)
        if not answered:
            return format_html('<span class="prava-muted">{}</span>', "Bu savolga hali javob berilmagan.")
        correct = sum(r["n"] for r in rows if r["is_correct"])
        percent = round(correct * 100 / answered)
        wrong = next((r for r in rows if not r["is_correct"]), None)
        hint = ""
        if wrong:
            hint = format_html(
                '<div class="prava-hint">Eng koʻp tanlangan xato variant: <strong>{}</strong> ({}%)</div>',
                wrong["selected_answer__text"], round(wrong["n"] * 100 / answered),
            )
        return format_html(
            '<div class="prava-stat-grid"><div><span>Javob berilgan</span><strong>{} marta</strong></div>'
            '<div><span>Toʻgʻri yechish</span><strong>{}%</strong></div></div>'
            '<div class="prava-split"><span>Toʻgʻri ({})</span><span>Xato ({})</span></div>'
            '<div class="prava-bar prava-bar--split"><i style="width:{}%"></i></div>{}',
            answered, percent, correct, answered - correct, percent, hint,
        )

    @action(description="Tanlanganlarni faollashtirish", icon="bolt")
    def activate(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} ta savol faollashtirildi.", messages.SUCCESS)

    @action(description="Tanlanganlarni oʻchirib qoʻyish (nofaol)", icon="pause_circle")
    def deactivate(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f"{n} ta savol nofaol qilindi — imtihon va mashqda chiqmaydi.", messages.WARNING)
