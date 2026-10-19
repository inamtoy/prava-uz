from django.contrib import admin

from .models import Exam, ExamAnswer


class ExamAnswerInline(admin.TabularInline):
    model = ExamAnswer
    extra = 0
    can_delete = False
    fields = ("order", "question", "selected_answer", "is_correct", "answered_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("question", "selected_answer")


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    inlines = [ExamAnswerInline]
    list_display = ("id", "user", "mode", "topic", "score", "total_questions", "is_passed", "status", "started_at")
    list_filter = ("mode", "status", "is_passed")
    list_select_related = ("user", "topic")
    search_fields = ("user__username", "user__email")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False  # faqat ko'rish
