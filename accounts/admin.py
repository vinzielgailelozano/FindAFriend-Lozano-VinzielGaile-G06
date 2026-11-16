from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "role", "course", "year_level", "is_active", "date_joined")
    list_filter = ("role", "student_status", "year_level", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "contact_number", "course")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("FindAFriend", {"fields": ("role", "contact_number", "profile_photo")}),
        ("Student details", {"fields": ("course", "year_level", "student_status", "interests", "bio")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("FindAFriend", {"fields": ("email", "first_name", "last_name", "role", "contact_number")}),
    )
