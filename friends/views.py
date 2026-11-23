from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from accounts.decorators import role_required
from accounts.models import User

from .forms import StudentSearchForm

STUDENT = User.Role.STUDENT


def _active_students():
    return User.objects.filter(role=STUDENT, is_active=True)


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
    cards = [(s, "none") for s in page.object_list]

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
    return render(request, "friends/student_detail.html", {"student": student})
