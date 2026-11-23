from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from accounts.decorators import role_required
from accounts.models import User
from friends import services as friend_services
from friends.models import FriendRequest


@never_cache
@login_required
def home(request):
    """Send each user to the dashboard for their role."""
    if request.user.role == User.Role.ADMIN:
        return redirect("dashboard:admin")
    return redirect("dashboard:student")


@never_cache
@role_required(User.Role.ADMIN)
def admin_dashboard(request):
    week_ago = timezone.now() - timedelta(days=7)
    students = User.objects.filter(role=User.Role.STUDENT)

    status_counts = dict(
        students.exclude(student_status="").values_list("student_status").annotate(n=Count("id"))
    )
    by_status = [
        {"label": label, "count": status_counts.get(value, 0)} for value, label in User.StudentStatus.choices
    ]

    context = {
        "total_students": students.count(),
        "total_admins": User.objects.filter(role=User.Role.ADMIN).count(),
        "new_this_week": students.filter(date_joined__gte=week_ago).count(),
        "needs_support": students.exclude(student_status__in=["", User.StudentStatus.REGULAR]).count(),
        "by_status": by_status,
        "recent_users": User.objects.order_by("-date_joined")[:5],
        "total_friendships": FriendRequest.objects.filter(status=FriendRequest.Status.ACCEPTED).count(),
        "total_pending": FriendRequest.objects.filter(status=FriendRequest.Status.PENDING).count(),
        "recent_connections": FriendRequest.objects.select_related("from_user", "to_user")[:5],
    }
    return render(request, "dashboard/admin_dashboard.html", context)


@never_cache
@role_required(User.Role.ADMIN)
def user_list(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "")
    users = User.objects.order_by("-date_joined")
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(course__icontains=query)
        )
    if role in User.Role.values:
        users = users.filter(role=role)
    return render(
        request,
        "dashboard/user_list.html",
        {"users": users, "query": query, "role": role, "roles": User.Role.choices},
    )


@never_cache
@role_required(User.Role.STUDENT)
def student_dashboard(request):
    me = request.user
    others = User.objects.filter(role=User.Role.STUDENT, is_active=True).exclude(pk=me.pk)
    same_course = others.filter(course__iexact=me.course) if me.course else others.none()

    # Suggestions: same course first, skipping friends and pending requests.
    connected = friend_services.friend_ids(me) | set(
        FriendRequest.objects.filter(from_user=me, status=FriendRequest.Status.PENDING).values_list("to_user_id", flat=True)
    ) | set(
        FriendRequest.objects.filter(to_user=me, status=FriendRequest.Status.PENDING).values_list("from_user_id", flat=True)
    )
    suggestions = list(same_course.exclude(pk__in=connected)[:3])
    if len(suggestions) < 3:
        extra = others.exclude(pk__in=connected).exclude(pk__in=[s.pk for s in suggestions]).order_by("-date_joined")
        suggestions += list(extra[: 3 - len(suggestions)])

    context = {
        "friend_count": len(friend_services.friend_ids(me)),
        "received_count": FriendRequest.objects.filter(to_user=me, status=FriendRequest.Status.PENDING).count(),
        "sent_count": FriendRequest.objects.filter(from_user=me, status=FriendRequest.Status.PENDING).count(),
        "same_course_count": same_course.count(),
        "suggestions": suggestions,
    }
    return render(request, "dashboard/student_dashboard.html", context)
