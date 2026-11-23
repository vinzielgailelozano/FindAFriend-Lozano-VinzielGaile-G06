from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from . import services
from .forms import FriendRequestForm, StudentSearchForm
from .models import FriendRequest

STUDENT = User.Role.STUDENT
ADMIN = User.Role.ADMIN


def _active_students():
    return User.objects.filter(role=STUDENT, is_active=True)


def _back(request, fallback, *args):
    """Redirect to ?next= if it is safe, otherwise to the fallback URL name."""
    target = request.POST.get("next") or request.GET.get("next")
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(fallback, *args)


def _error_text(exc):
    return " ".join(exc.messages)


# ---------------------------------------------------------------------------
# READ: find students
# ---------------------------------------------------------------------------
@never_cache
@role_required(STUDENT)
def student_list(request):
    form = StudentSearchForm(request.GET or None)
    students = _active_students().exclude(pk=request.user.pk).order_by("first_name", "last_name")

    if form.is_valid():
        data = form.cleaned_data
        if data["q"]:
            q = data["q"]
            students = students.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(username__icontains=q)
                | Q(interests__icontains=q)
                | Q(bio__icontains=q)
            )
        if data["course"]:
            students = students.filter(course__icontains=data["course"])
        if data["year_level"]:
            students = students.filter(year_level=data["year_level"])
        if data["student_status"]:
            students = students.filter(student_status=data["student_status"])

    page = Paginator(students, 12).get_page(request.GET.get("page"))
    states = services.relationship_map(request.user, page.object_list)
    cards = [(s, states.get(s.pk, "none")) for s in page.object_list]

    query = request.GET.copy()
    query.pop("page", None)
    return render(
        request,
        "friends/student_list.html",
        {"form": form, "page": page, "cards": cards, "querystring": query.urlencode()},
    )


@never_cache
@role_required(STUDENT)
def student_detail(request, pk):
    student = get_object_or_404(_active_students(), pk=pk)
    if student.pk == request.user.pk:
        return redirect("accounts:profile")
    state, fr = services.relationship(request.user, student)
    return render(
        request,
        "friends/student_detail.html",
        {
            "student": student,
            "state": state,
            "friend_request": fr,
            "form": FriendRequestForm() if state == "none" else None,
        },
    )


# ---------------------------------------------------------------------------
# CREATE: send a friend request
# ---------------------------------------------------------------------------
@require_POST
@role_required(STUDENT)
def send_request(request, pk):
    student = get_object_or_404(_active_students(), pk=pk)
    form = FriendRequestForm(request.POST)
    if not form.is_valid():
        state, fr = services.relationship(request.user, student)
        messages.error(request, "Please fix the message and try again.")
        return render(
            request,
            "friends/student_detail.html",
            {"student": student, "state": state, "friend_request": fr, "form": form},
            status=400,
        )
    try:
        services.send_friend_request(request.user, student, form.cleaned_data["message"])
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
    else:
        messages.success(request, f"Friend request sent to {student.first_name or student.username}!")
    return _back(request, "friends:student_detail", student.pk)


# ---------------------------------------------------------------------------
# READ: my requests
# ---------------------------------------------------------------------------
@never_cache
@role_required(STUDENT)
def request_list(request):
    pending = FriendRequest.Status.PENDING
    received = (
        FriendRequest.objects.filter(to_user=request.user, status=pending).select_related("from_user")
    )
    sent = FriendRequest.objects.filter(from_user=request.user, status=pending).select_related("to_user")
    return render(request, "friends/request_list.html", {"received": received, "sent": sent})


# ---------------------------------------------------------------------------
# UPDATE: accept / decline a received request, edit a sent request's message
# ---------------------------------------------------------------------------
@require_POST
@role_required(STUDENT)
def respond_request(request, pk, action):
    if action not in ("accept", "decline"):
        raise Http404("Unknown action")
    fr = get_object_or_404(FriendRequest, pk=pk, to_user=request.user)
    accept = action == "accept"
    try:
        services.respond_to_request(fr, request.user, accept=accept)
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
    else:
        name = fr.from_user.first_name or fr.from_user.username
        if accept:
            messages.success(request, f"You and {name} are now friends!")
        else:
            messages.info(request, f"You declined {name}'s request.")
    return _back(request, "friends:request_list")


@never_cache
@role_required(STUDENT)
def request_edit(request, pk):
    fr = get_object_or_404(
        FriendRequest, pk=pk, from_user=request.user, status=FriendRequest.Status.PENDING
    )
    if request.method == "POST":
        form = FriendRequestForm(request.POST, instance=fr)
        if form.is_valid():
            form.save()
            messages.success(request, "Your request message was updated.")
            return redirect("friends:request_list")
        messages.error(request, "Please fix the errors below.")
    else:
        form = FriendRequestForm(instance=fr)
    return render(request, "friends/request_form.html", {"form": form, "friend_request": fr})


# ---------------------------------------------------------------------------
# DELETE: cancel a sent request, unfriend
# ---------------------------------------------------------------------------
@never_cache
@role_required(STUDENT)
def request_cancel(request, pk):
    fr = get_object_or_404(
        FriendRequest, pk=pk, from_user=request.user, status=FriendRequest.Status.PENDING
    )
    name = fr.to_user.first_name or fr.to_user.username
    if request.method == "POST":
        fr.delete()
        messages.success(request, f"Your request to {name} was cancelled.")
        return redirect("friends:request_list")
    return render(
        request,
        "friends/confirm_delete.html",
        {
            "title": "Cancel friend request?",
            "text": f"{name} will no longer see your request. You can send a new one later.",
            "button": "Cancel request",
            "back_url": "friends:request_list",
        },
    )


@never_cache
@role_required(STUDENT)
def friend_list(request):
    q = request.GET.get("q", "").strip()
    friends = services.friends_of(request.user)
    if q:
        friends = friends.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q) | Q(course__icontains=q)
        )
    return render(request, "friends/friend_list.html", {"friends": friends, "q": q})


@never_cache
@role_required(STUDENT)
def unfriend(request, pk):
    friend = get_object_or_404(User, pk=pk)
    friendship = services.friendship_between(request.user, friend)
    if friendship is None:
        messages.error(request, "You aren't friends with this student.")
        return redirect("friends:friend_list")
    name = friend.first_name or friend.username
    if request.method == "POST":
        friendship.delete()
        messages.success(request, f"You removed {name} from your friends.")
        return redirect("friends:friend_list")
    return render(
        request,
        "friends/confirm_delete.html",
        {
            "title": f"Remove {name} from your friends?",
            "text": "They won't be told, but you'll need to send a new request to connect again.",
            "button": "Unfriend",
            "back_url": "friends:friend_list",
        },
    )


# ---------------------------------------------------------------------------
# ADMIN: view and moderate all connections
# ---------------------------------------------------------------------------
@never_cache
@role_required(ADMIN)
def admin_connections(request):
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    rows = FriendRequest.objects.select_related("from_user", "to_user")
    if status in FriendRequest.Status.values:
        rows = rows.filter(status=status)
    if q:
        rows = rows.filter(
            Q(from_user__username__icontains=q)
            | Q(to_user__username__icontains=q)
            | Q(from_user__first_name__icontains=q)
            | Q(to_user__first_name__icontains=q)
            | Q(from_user__last_name__icontains=q)
            | Q(to_user__last_name__icontains=q)
        )
    page = Paginator(rows, 20).get_page(request.GET.get("page"))
    all_rows = FriendRequest.objects.all()
    return render(
        request,
        "friends/admin_connections.html",
        {
            "page": page,
            "status": status,
            "q": q,
            "statuses": FriendRequest.Status.choices,
            "count_friends": all_rows.filter(status=FriendRequest.Status.ACCEPTED).count(),
            "count_pending": all_rows.filter(status=FriendRequest.Status.PENDING).count(),
            "count_declined": all_rows.filter(status=FriendRequest.Status.DECLINED).count(),
        },
    )


@never_cache
@role_required(ADMIN)
def admin_connection_delete(request, pk):
    fr = get_object_or_404(FriendRequest.objects.select_related("from_user", "to_user"), pk=pk)
    if request.method == "POST":
        fr.delete()
        messages.success(request, "The connection record was removed.")
        return redirect("friends:admin_connections")
    return render(
        request,
        "friends/confirm_delete.html",
        {
            "title": "Remove this connection?",
            "text": f"{fr.from_user.username} → {fr.to_user.username} ({fr.get_status_display()}). "
            "Use this for spam or reported requests. This can't be undone.",
            "button": "Remove",
            "back_url": "friends:admin_connections",
        },
    )
