from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class UsernameOrEmailBackend(ModelBackend):
    """Authenticate with either a username or an email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if not username or not password:
            return None

        lookup = "email__iexact" if "@" in username else "username__iexact"
        try:
            user = UserModel._default_manager.get(**{lookup: username})
        except (UserModel.DoesNotExist, UserModel.MultipleObjectsReturned):
            # Run the hasher once to reduce timing differences between
            # existing and non-existing users.
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
