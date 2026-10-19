from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class BootstrapMixin:
    def _style_fields(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control form-control-lg")

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                widget = self.fields[name].widget
                widget.attrs["class"] = widget.attrs.get("class", "") + " is-invalid"


class RegisterForm(BootstrapMixin, UserCreationForm):
    first_name = forms.CharField(label="Ismingiz", max_length=150)
    email = forms.EmailField(label="Email")

    class Meta:
        model = User
        fields = ("first_name", "username", "email")
        labels = {"username": "Foydalanuvchi nomi (login)"}
        help_texts = {"username": "Faqat harflar, raqamlar va @/./+/-/_ belgilar."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Parol"
        self.fields["password2"].label = "Parolni takrorlang"
        self.fields["password2"].help_text = "Tekshirish uchun parolni yana bir bor kiriting."
        self._style_fields()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Bu email bilan allaqachon roʻyxatdan oʻtilgan.")
        return email


class LoginForm(BootstrapMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": "Login (yoki email) yoki parol notoʻgʻri.",
        "inactive": "Bu akkaunt faol emas.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Login yoki email"
        self.fields["password"].label = "Parol"
        self._style_fields()
