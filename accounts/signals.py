from django.contrib import messages
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

# fail_silently=True: some logins (e.g. the test client) happen without the
# messages middleware, and a greeting should never break a login/logout.


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    if request is not None:
        messages.success(request, f"Welcome back, {user.first_name or user.username}!", fail_silently=True)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if request is not None:
        messages.info(request, "You have been logged out.", fail_silently=True)
