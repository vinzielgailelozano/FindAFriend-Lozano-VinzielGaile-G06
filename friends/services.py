"""Business rules for friend connections.

Views call these functions so every rule is enforced in one place.
They raise ValidationError with a message that can be shown to the user.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import User

from .models import FriendRequest

MAX_PENDING_SENT = 20


def requests_between(a, b):
    return FriendRequest.objects.filter(
        Q(from_user=a, to_user=b) | Q(from_user=b, to_user=a)
    )


def friendship_between(a, b):
    return requests_between(a, b).filter(status=FriendRequest.Status.ACCEPTED).first()


def friend_ids(user):
    rows = FriendRequest.objects.filter(
        Q(from_user=user) | Q(to_user=user), status=FriendRequest.Status.ACCEPTED
    ).values_list("from_user_id", "to_user_id")
    return {b if a == user.pk else a for a, b in rows}


def friends_of(user):
    return User.objects.filter(pk__in=friend_ids(user)).order_by("first_name", "last_name")


def relationship(me, other):
    """Describe how `me` is connected to `other`.

    Returns (state, friend_request) where state is one of:
    "self", "friends", "sent", "received", "none".
    """
    if me.pk == other.pk:
        return "self", None
    for fr in requests_between(me, other):
        if fr.status == FriendRequest.Status.ACCEPTED:
            return "friends", fr
        if fr.status == FriendRequest.Status.PENDING:
            return ("sent" if fr.from_user_id == me.pk else "received"), fr
    return "none", None


def relationship_map(me, users):
    """{user_id: state} for many users at once (used on the search page)."""
    ids = [u.pk for u in users]
    states = {}
    rows = FriendRequest.objects.filter(
        Q(from_user=me, to_user_id__in=ids) | Q(to_user=me, from_user_id__in=ids)
    ).exclude(status=FriendRequest.Status.DECLINED)
    for fr in rows:
        other_id = fr.to_user_id if fr.from_user_id == me.pk else fr.from_user_id
        if fr.status == FriendRequest.Status.ACCEPTED:
            states[other_id] = "friends"
        elif states.get(other_id) != "friends":
            states[other_id] = "sent" if fr.from_user_id == me.pk else "received"
    return states


@transaction.atomic
def send_friend_request(from_user, to_user, message=""):
    name = to_user.first_name or to_user.username

    if from_user.pk == to_user.pk:
        raise ValidationError("You can't send a friend request to yourself.")
    if to_user.role != User.Role.STUDENT or not to_user.is_active:
        raise ValidationError("You can only send friend requests to active students.")

    state, _ = relationship(from_user, to_user)
    if state == "friends":
        raise ValidationError(f"You and {name} are already friends.")
    if state == "sent":
        raise ValidationError(f"You already sent {name} a friend request.")
    if state == "received":
        raise ValidationError(f"{name} already sent you a request. Accept it in Friend Requests.")

    pending_count = FriendRequest.objects.filter(
        from_user=from_user, status=FriendRequest.Status.PENDING
    ).count()
    if pending_count >= MAX_PENDING_SENT:
        raise ValidationError(
            f"You have {MAX_PENDING_SENT} requests waiting for a reply. Cancel some before sending more."
        )

    # A previously declined request is reused (one row per direction).
    fr, _created = FriendRequest.objects.update_or_create(
        from_user=from_user,
        to_user=to_user,
        defaults={"message": message, "status": FriendRequest.Status.PENDING, "responded_at": None},
    )
    return fr


def respond_to_request(fr, user, accept):
    if fr.to_user_id != user.pk:
        raise ValidationError("You can only answer requests sent to you.")
    if not fr.is_pending:
        raise ValidationError("This request was already answered.")
    fr.status = FriendRequest.Status.ACCEPTED if accept else FriendRequest.Status.DECLINED
    fr.responded_at = timezone.now()
    fr.save(update_fields=["status", "responded_at", "updated_at"])
    return fr
