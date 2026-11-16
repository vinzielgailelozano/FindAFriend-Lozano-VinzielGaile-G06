from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from accounts.decorators import role_required
from accounts.models import User


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
    context = {
        "same_course_count": same_course.count(),
        "same_course_year_count": same_course.filter(year_level=me.year_level).count() if me.year_level else 0,
        "same_status_count": others.filter(student_status=me.student_status).count() if me.student_status else 0,
    }
    return render(request, "dashboard/student_dashboard.html", context)
