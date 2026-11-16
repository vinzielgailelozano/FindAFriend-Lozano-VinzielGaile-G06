from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm

from .models import User


class StyledFormMixin:
    """Adds the project's CSS class to every widget."""

    def _style_fields(self):
        for name, field in self.fields.items():
            css = "input"
            if isinstance(field.widget, forms.ClearableFileInput):
                css = "input input-file"
            field.widget.attrs.setdefault("class", css)
            if field.required:
                field.widget.attrs.setdefault("required", "required")


class RegistrationForm(StyledFormMixin, UserCreationForm):
    """Student self-registration.

    UserCreationForm already validates that the username is unique, that
    password1 and password2 match, and runs AUTH_PASSWORD_VALIDATORS. It also
    stores the password with set_password(), so it is hashed.
    """

    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(
        required=True,
        error_messages={"invalid": "Enter a valid email address, e.g. juan@email.com."},
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("first_name", "last_name", "username", "email", "course", "year_level", "student_status", "contact_number")
        help_texts = {"username": "Letters, digits and @/./+/-/_ only."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contact_number"].help_text = "Optional. e.g. 09171234567"
        self.fields["course"].widget.attrs["placeholder"] = "e.g. BS Information Technology"
        self.fields["year_level"].choices = [("", "Select year level")] + list(User.YearLevel.choices)
        self.fields["student_status"].choices = [("", "Select status")] + list(User.StudentStatus.choices)
        for name in ("course", "year_level", "student_status"):
            self.fields[name].required = True
        self.fields["password1"].label = "Password"
        self.fields["password2"].label = "Confirm password"
        self.fields["first_name"].widget.attrs["autofocus"] = True
        self.fields["username"].widget.attrs.pop("autofocus", None)
        self._style_fields()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_username(self):
        username = super().clean_username()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        # Public registration can only ever create Student accounts.
        user.role = User.Role.STUDENT
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
        return user


class LoginForm(StyledFormMixin, AuthenticationForm):
    error_messages = {
        "invalid_login": "Invalid username/email or password. Please try again.",
        "inactive": "This account is inactive. please contact an admin.",
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request, *args, **kwargs)
        self.fields["username"].label = "Username or email"
        self._style_fields()


class ProfileForm(StyledFormMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = (
            "first_name", "last_name", "email", "contact_number",
            "course", "year_level", "student_status", "interests", "bio", "profile_photo",
        )
        widgets = {
            "profile_photo": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "bio": forms.Textarea(attrs={"rows": 3, "placeholder": "A short intro other students will see"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["contact_number"].help_text = "e.g. 09171234567"
        self._style_fields()

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Another account is already using this email.")
        return email

    def clean_profile_photo(self):
        photo = self.cleaned_data.get("profile_photo")
        if photo and hasattr(photo, "size") and photo.size > 2 * 1024 * 1024:
            raise forms.ValidationError("Profile photo must be 2 MB or smaller.")
        return photo


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style_fields()
