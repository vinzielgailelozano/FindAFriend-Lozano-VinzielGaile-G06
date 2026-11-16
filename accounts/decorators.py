from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(*roles):
    """Allow a view only for logged-in users whose role is in `roles`.

    * Logged-out users are sent to the login page (via @login_required).
    * Logged-in users with the wrong role are sent back to their own
      dashboard, so typing another role's URL never shows its content.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                messages.error(request, "You don't have permission to open that page.")
                return redirect("dashboard:home")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
