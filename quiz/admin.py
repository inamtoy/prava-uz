from django.contrib import admin, messages
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import RelatedDropdownFilter
from unfold.decorators import action, display

from config.admin_ui import PravaListMixin, pill, tab
from results.dashboard import MIN_QUESTION_ANSWERS, MIN_TOPIC_ANSWERS, MIN_TOPIC_QUESTIONS
from results.models import Exam, ExamAnswer

from .forms import AnswerInlineFormSet
from .models import Answer, Question, Topic

FINISHED = (Exam.STATUS_FINISHED, Exam.STATUS_EXPIRED)
SIDE = "prava-side"  # change_form.html bu fieldset'larni o'ng ustunga chiqaradi
TOPIC_ICONS = {  # slug bo'lagi -> Material Symbols belgisi (bezak, ma'lumot emas)
    "umumiy": "menu_book", "belgi": "signpost", "svetofor": "traffic", "chorraha": "fork_right",
    "quvib": "directions_car", "tibbiy": "medical_services", "tezlik": "speed",
}


def topic_icon(topic):
    return next((icon for key, icon in TOPIC_ICONS.items() if key in topic.slug), "topic")


def topic_chip(topic):
    return format_html('<span class="prava-tag prava-tag--{}">{}</span>', topic.order % 6, topic.name)


def answered_stats():
    """Yakunlangan imtihonlardagi javob berilgan savollar: savol bo'yicha jami va to'g'ri."""
    return (
        ExamAnswer.objects.filter(exam__status__in=FINISHED, selected_answer__isnull=False)
        .values("question")
        .annotate(total=Count("id"), correct=Count("id", filter=Q(is_correct=True)))
    )


def rate_tone(percent):
    if percent < 50:
        return "bad", "Qiyin"
    if percent < 70:
        return "mid", "Oʻrtacha"
    if percent < 85:
        return "ok", "Yaxshi"
    return "ok", "Oson"


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


class HardFilter(admin.SimpleListFilter):
    """Qiyin savollar: kamida MIN_QUESTION_ANSWERS ta javobdan yarmidan ko'pi xato."""
    title = "qiyinlik"
    parameter_name = "qiyin"

    def lookups(self, request, model_admin):
        return [("ha", "Qiyin (>50% xato)")]

    def queryset(self, request, queryset):
        if self.value() == "ha":  # QuestionAdmin.get_queryset annotatsiyalari
            return queryset.filter(_answered__gte=MIN_QUESTION_ANSWERS).alias(_correct2=F("_correct") * 2).filter(_correct2__lt=F("_answered"))
        return queryset


@admin.register(Topic)
class TopicAdmin(PravaListMixin, ModelAdmin):
    list_display = ("topic_card", "question_count", "correct_rate", "recommendation", "links")
    list_display_links = ("topic_card",)
    list_per_page = 30
    ordering = ("order", "name")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "description")
    list_head_title = "Biletlarni boshqarish"
    list_head_subtitle = "Imtihon savollari boʻlingan biletlar roʻyxati, tartibi va sozlamalari."
    fieldsets = (
        (None, {"fields": ("name", "slug", "description", "order")}),
    )

    def get_queryset(self, request):
        answered = Q(questions__exam_answers__selected_answer__isnull=False,
                     questions__exam_answers__exam__status__in=FINISHED)
        return super().get_queryset(request).annotate(
            _question_count=Count("questions", distinct=True),
            _active_count=Count("questions", filter=Q(questions__is_active=True), distinct=True),
            _answered=Count("questions__exam_answers", filter=answered, distinct=True),
            _correct=Count("questions__exam_answers",
                           filter=answered & Q(questions__exam_answers__is_correct=True), distinct=True),
        )

    def get_list_head(self, request):
        return {
            "count_label": f"{Topic.objects.count()} ta bilet",
            "actions": [{"label": "Yangi bilet", "icon": "add", "style": "accent", "url": reverse("admin:quiz_topic_add")}],
        }

    @display(description="Bilet", ordering="order")
    def topic_card(self, obj):
        desc = obj.description if len(obj.description) <= 90 else obj.description[:88] + "…"
        return format_html(
            '<div class="prava-topic"><span class="prava-topic__icon prava-tag--{} material-symbols-outlined">{}</span>'
            '<span class="prava-topic__text"><strong>{}</strong><span class="prava-muted">{}</span></span></div>',
            obj.order % 6, topic_icon(obj), obj.name, desc,
        )

    @display(description="Savollar", ordering="_active_count")
    def question_count(self, obj):
        inactive = obj._question_count - obj._active_count
        extra = format_html(' <span class="prava-muted">+{} nofaol</span>', inactive) if inactive else ""
        return format_html('<span class="prava-chip">{} ta faol</span>{}', obj._active_count, extra)

    @display(description="Toʻgʻri javob %", ordering="_correct")
    def correct_rate(self, obj):
        if not obj._answered:
            return format_html('<span class="prava-muted">{}</span>', "Hali javob yoʻq")
        percent = round(obj._correct * 100 / obj._answered)
        tone, _ = rate_tone(percent)
        return format_html(
            '<div class="prava-rate prava-rate--{}"><strong>{}%</strong><span class="prava-muted">{} ta javob</span>'
            '<div class="prava-bar"><i style="width:{}%"></i></div></div>',
            tone, percent, obj._answered, percent,
        )

    @display(description="Tavsiya")
    def recommendation(self, obj):
        if obj._active_count < MIN_TOPIC_QUESTIONS:
            return format_html('<span class="prava-tag prava-tag--warn" title="Har biletda kamida {} ta faol savol tavsiya etiladi">{} tadan kam savol</span>',
                               MIN_TOPIC_QUESTIONS, MIN_TOPIC_QUESTIONS)
        if obj._answered >= MIN_TOPIC_ANSWERS and obj._correct * 100 / obj._answered < 60:
            return format_html('<span class="prava-tag prava-tag--bad">{}</span>', "Qiyin bilet")
        return format_html('<span class="prava-tag prava-tag--ok">{}</span>', "Tayyor")

    @display(description="")
    def links(self, obj):
        url = reverse("admin:quiz_question_changelist") + f"?topic__id__exact={obj.pk}"
        return format_html('<a class="prava-link" href="{}">Savollarni koʻrish →</a>', url)


@admin.register(Question)
class QuestionAdmin(PravaListMixin, ModelAdmin):
    inlines = [AnswerInline]
    list_display = ("thumbnail", "short_text", "topic_badge", "correct_answer", "correct_rate", "status_badge")
    list_display_links = ("thumbnail", "short_text")
    list_filter = (("topic", RelatedDropdownFilter), "is_active", HasImageFilter, ExplanationFilter, HardFilter)
    filter_params = ("topic__id__exact", "is_active__exact", "rasm", "izoh", "qiyin")
    list_head_title = "Savollar"
    list_head_subtitle = "Imtihon savollari bazasi, biletlar va koʻrsatkichlarni boshqarish."
    list_filter_submit = True
    list_select_related = ("topic",)
    list_per_page = 30
    # "12-bilet" yoki savol ID'si bilan ham qidiriladi
    search_fields = ("text", "explanation", "=topic__name", "=id")
    search_help_text = "Savol matni, izoh, bilet nomi (masalan «12-bilet») yoki ID"
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
        ("Bilet", {"fields": ("topic",), "classes": [SIDE]}),
        ("Savol rasmi", {"fields": ("image",), "classes": [SIDE]}),
        ("Savol statistikasi", {"fields": ("question_stats",), "classes": [SIDE, "prava-stats"]}),
    )

    def get_queryset(self, request):
        answered = Q(exam_answers__selected_answer__isnull=False, exam_answers__exam__status__in=FINISHED)
        return super().get_queryset(request).annotate(
            _answers=Count("answers", distinct=True),
            _answered=Count("exam_answers", filter=answered, distinct=True),
            _correct=Count("exam_answers", filter=answered & Q(exam_answers__is_correct=True), distinct=True),
            _correct_text=Subquery(
                Answer.objects.filter(question=OuterRef("pk"), is_correct=True).values("text")[:1]
            ),
        )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in ("text", "explanation"):  # standart 10 qator — forma juda uzun edi
            field.widget.attrs["rows"] = 3 if db_field.name == "text" else 4
        return field

    def _neighbours(self, obj):
        """Bilet ichidagi o'rni va oldingi/keyingi savol; bilet chegarasida qo'shni biletga o'tadi."""
        ids = list(Question.objects.filter(topic=obj.topic).order_by("id").values_list("id", flat=True))
        pos = ids.index(obj.pk)
        prev_id = ids[pos - 1] if pos else (
            Question.objects.filter(topic__order__lt=obj.topic.order)
            .order_by("-topic__order", "-id").values_list("id", flat=True).first()
        )
        next_id = ids[pos + 1] if pos + 1 < len(ids) else (
            Question.objects.filter(topic__order__gt=obj.topic.order)
            .order_by("topic__order", "id").values_list("id", flat=True).first()
        )
        return prev_id, next_id, pos + 1, len(ids)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        obj = self.get_object(request, object_id)
        if obj is not None:
            prev_id, next_id, pos, total = self._neighbours(obj)
            extra_context = {
                **(extra_context or {}),
                "prava_nav": {
                    "topic": obj.topic, "pos": pos, "total": total,
                    "prev_url": reverse("admin:quiz_question_change", args=[prev_id]) if prev_id else "",
                    "next_url": reverse("admin:quiz_question_change", args=[next_id]) if next_id else "",
                    "topic_url": reverse("admin:quiz_question_changelist") + f"?topic__id__exact={obj.topic_id}",
                },
            }
        return super().change_view(request, object_id, form_url, extra_context)

    def response_change(self, request, obj):
        if "_savenext" in request.POST:
            next_id = self._neighbours(obj)[1]
            self.message_user(request, f"{obj.topic.name}: savol saqlandi.", messages.SUCCESS)
            if next_id:
                return HttpResponseRedirect(reverse("admin:quiz_question_change", args=[next_id]))
            return HttpResponseRedirect(reverse("admin:quiz_question_changelist"))
        return super().response_change(request, obj)

    def get_list_head(self, request):
        counts = Question.objects.aggregate(
            total=Count("id"),
            active=Count("id", filter=Q(is_active=True)),
            with_image=Count("id", filter=~Q(image="") & Q(image__isnull=False)),
            no_explanation=Count("id", filter=Q(explanation="")),
        )
        hard = (
            answered_stats().filter(total__gte=MIN_QUESTION_ANSWERS)
            .alias(correct2=F("correct") * 2).filter(correct2__lt=F("total")).count()
        )
        return {
            "count_label": f"{counts['total']} ta savol",
            "actions": [{"label": "Yangi savol", "icon": "add", "style": "accent", "url": reverse("admin:quiz_question_add")}],
            "tabs": [
                tab(request, "is_active__exact", None, "Hammasi", counts["total"]),
                tab(request, "is_active__exact", "1", "Faol", counts["active"]),
                tab(request, "is_active__exact", "0", "Nofaol", counts["total"] - counts["active"]),
            ],
            "pills": [
                pill(request, "rasm", "bor", "Faqat rasmli", counts["with_image"]),
                pill(request, "izoh", "yoq", "Izohsiz", counts["no_explanation"], tone="warn"),
                pill(request, "qiyin", "ha", "Qiyin savollar (>50% xato)", hard, tone="bad"),
            ],
        }

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

    @display(description="Bilet", ordering="topic__order")
    def topic_badge(self, obj):
        return topic_chip(obj.topic)

    @display(description="Toʻgʻri javob")
    def correct_answer(self, obj):
        text = obj._correct_text or "—"
        text = text if len(text) <= 60 else text[:58] + "…"
        return format_html('<span class="prava-correct">{}</span><div class="prava-muted">{} ta variant</div>', text, obj._answers)

    @display(description="Toʻgʻri javob %", ordering="_correct")
    def correct_rate(self, obj):
        if not obj._answered:
            return format_html('<span class="prava-muted">{}</span>', "Hali javob yoʻq")
        if obj._answered < MIN_QUESTION_ANSWERS:
            return format_html('<span class="prava-muted" title="Foiz {} ta javobdan keyin koʻrsatiladi">{} ta javob</span>',
                               MIN_QUESTION_ANSWERS, obj._answered)
        percent = round(obj._correct * 100 / obj._answered)
        tone, word = rate_tone(percent)
        return format_html(
            '<div class="prava-rate prava-rate--{}" title="{} ta javob asosida"><strong>{}%</strong>'
            '<span class="prava-muted">{}</span><div class="prava-bar"><i style="width:{}%"></i></div></div>',
            tone, obj._answered, percent, word, percent,
        )

    @display(description="Holat", ordering="is_active", label={"Faol": "success", "Nofaol": "warning"})
    def status_badge(self, obj):
        return "Faol" if obj.is_active else "Nofaol"

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
