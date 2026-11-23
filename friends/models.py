from django.conf import settings
from django.db import models
from django.db.models import F, Q


class FriendRequest(models.Model):
    """A friend request from one student to another.

    * PENDING  - waiting for the receiver to answer
    * ACCEPTED - the two students are friends (this row *is* the friendship)
    * DECLINED - the receiver said no; the sender may send again later

    Cancelling a pending request or unfriending deletes the row.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_friend_requests",
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friend_requests",
    )
    message = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(from_user=F("to_user")),
                name="friend_request_not_to_self",
            ),
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                name="unique_friend_request_per_pair",
            ),
        ]

    def __str__(self):
        return f"{self.from_user} → {self.to_user} ({self.get_status_display()})"

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    def other_user(self, user):
        """The person on the other side of this request/friendship."""
        return self.to_user if self.from_user_id == user.pk else self.from_user
