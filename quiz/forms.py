from django import forms
from django.core.exceptions import ValidationError


class AnswerInlineFormSet(forms.BaseInlineFormSet):
    """Savolda 2–4 ta javob va aynan bitta to'g'ri javob bo'lishi shart."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        total = correct = 0
        for form in self.forms:
            data = getattr(form, "cleaned_data", None)
            if not data or data.get("DELETE") or not data.get("text"):
                continue
            total += 1
            if data.get("is_correct"):
                correct += 1
        if total < 2:
            raise ValidationError("Savolda kamida 2 ta javob boʻlishi kerak.")
        if total > 4:
            raise ValidationError("Savolda koʻpi bilan 4 ta javob boʻlishi mumkin.")
        if correct != 1:
            raise ValidationError("Aynan bitta javob toʻgʻri deb belgilanishi kerak (hozir: %d ta)." % correct)
