from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Username yoki email + parol bilan kirish."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if not username or password is None:
            return None
        User = get_user_model()
        lookup = {"email__iexact": username} if "@" in username else {"username__iexact": username}
        try:
            user = User.objects.get(**lookup)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            User().set_password(password)  # vaqt bo'yicha hujumlarni yumshatish
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
