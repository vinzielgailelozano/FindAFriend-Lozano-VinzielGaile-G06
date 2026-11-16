from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.core.validators import RegexValidator
from django.db import models

phone_validator = RegexValidator(
    regex=r"^(09|\+639)\d{9}$",
    message="Enter a valid PH mobile number, e.g. 09171234567 or +639171234567.",
)


class UserManager(DjangoUserManager):
    """Superusers created with `createsuperuser` automatically get the Admin role."""

    use_in_migrations = True

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Custom user for FindAFriend.

    Roles:
      * ADMIN   - moderators who manage users and handle reports
      * STUDENT - students looking for friends, classmates and study buddies
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        STUDENT = "STUDENT", "Student"

    class YearLevel(models.IntegerChoices):
        FIRST = 1, "1st Year"
        SECOND = 2, "2nd Year"
        THIRD = 3, "3rd Year"
        FOURTH = 4, "4th Year"
        FIFTH = 5, "5th Year"

    class StudentStatus(models.TextChoices):
        REGULAR = "REGULAR", "Regular"
        IRREGULAR = "IRREGULAR", "Irregular"
        TRANSFEREE = "TRANSFEREE", "Transferee"
        SHIFTEE = "SHIFTEE", "Shiftee"
        EXCHANGE = "EXCHANGE", "Exchange student"

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STUDENT)
    contact_number = models.CharField(max_length=13, blank=True, validators=[phone_validator])
    profile_photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)

    # Student details (used later for search, filters and friend matching)
    course = models.CharField("course / program", max_length=100, blank=True)
    year_level = models.PositiveSmallIntegerField(choices=YearLevel.choices, blank=True, null=True)
    student_status = models.CharField(max_length=12, choices=StudentStatus.choices, blank=True)
    bio = models.TextField(max_length=300, blank=True)
    interests = models.CharField(
        "interests & hobbies", max_length=255, blank=True, help_text="Separate with commas, e.g. badminton, anime, coding"
    )

    objects = UserManager()

    REQUIRED_FIELDS = ["email"]

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def initials(self):
        first = (self.first_name[:1] or self.username[:1]).upper()
        last = self.last_name[:1].upper()
        return f"{first}{last}"

    @property
    def interest_list(self):
        return [i.strip() for i in self.interests.split(",") if i.strip()]

    @property
    def profile_completion(self):
        """Percent of optional profile fields filled in (shown on the dashboard)."""
        fields = [self.profile_photo, self.course, self.year_level, self.student_status, self.bio, self.interests]
        return round(100 * sum(1 for f in fields if f) / len(fields))
