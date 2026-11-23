from .models import FriendRequest


def friend_request_count(request):
    """Number of pending requests waiting for the logged-in student (sidebar badge)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or getattr(user, "role", None) != "STUDENT":
        return {}
    count = FriendRequest.objects.filter(to_user=user, status=FriendRequest.Status.PENDING).count()
    return {"pending_request_count": count}
