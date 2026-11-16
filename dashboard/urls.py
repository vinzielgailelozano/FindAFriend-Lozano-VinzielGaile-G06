from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", views.admin_dashboard, name="admin"),
    path("admin/users/", views.user_list, name="user_list"),
    path("student/", views.student_dashboard, name="student"),
]
