from django.urls import path

from . import views

app_name = "friends"

urlpatterns = [
    # Students
    path("students/", views.student_list, name="student_list"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/add/", views.send_request, name="send_request"),
    path("requests/", views.request_list, name="request_list"),
    path("requests/<int:pk>/edit/", views.request_edit, name="request_edit"),
    path("requests/<int:pk>/cancel/", views.request_cancel, name="request_cancel"),
    path("requests/<int:pk>/<str:action>/", views.respond_request, name="respond_request"),
    path("", views.friend_list, name="friend_list"),
    path("<int:pk>/unfriend/", views.unfriend, name="unfriend"),
    # Admin
    path("connections/", views.admin_connections, name="admin_connections"),
    path("connections/<int:pk>/delete/", views.admin_connection_delete, name="admin_connection_delete"),
]
