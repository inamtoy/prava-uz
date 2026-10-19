from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .forms import AnswerInlineFormSet
from .models import Answer, Question, Topic


class AnswerInline(admin.TabularInline):
    model = Answer
    formset = AnswerInlineFormSet
    extra = 4
    max_num = 4
    min_num = 0


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "question_count")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_question_count=Count("questions"))

    @admin.display(description="Savollar soni", ordering="_question_count")
    def question_count(self, obj):
        return obj._question_count


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerInline]
    list_display = ("id", "short_text", "topic", "has_image", "is_active")
    list_filter = ("topic", "is_active")
    list_select_related = ("topic",)
    search_fields = ("text",)
    readonly_fields = ("image_preview", "created_at")
    fields = ("topic", "text", "image", "image_preview", "explanation", "is_active", "created_at")

    @admin.display(description="Savol")
    def short_text(self, obj):
        return obj.text[:70] + ("…" if len(obj.text) > 70 else "")

    @admin.display(description="Rasm", boolean=True)
    def has_image(self, obj):
        return bool(obj.image)

    @admin.display(description="Rasm koʻrinishi")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:120px">', obj.image.url)
        return "—"
